"""
Drain — Online log parsing with a fixed-depth tree.

Reference
---------
Pinjia He, Jieming Zhu, Zibin Zheng, Michael R. Lyu.
*Drain: An Online Log Parsing Approach with Fixed Depth Tree*.
IEEE International Conference on Web Services (ICWS), 2017.

This module implements a faithful, dependency-free version of Drain plus a
``StructuredLogFeaturizer`` that converts parsed events into a sparse feature
matrix consumable by scikit-learn classifiers.

Why a custom implementation (instead of pip install drain3)?
    1. Zero extra runtime dependency.
    2. Full transparency for thesis discussion — every line is reviewable.
    3. Pickle-friendly: parser state ships inside the existing model bundle.

Public API
----------
``DrainLogParser``        — incremental log-template miner.
``ParsedLog``             — dataclass returned by ``parse_line`` / ``parse_batch``.
``StructuredLogFeaturizer`` — sklearn-style ``fit`` / ``transform`` adapter that
                              produces structured ML features (template id,
                              log level, service name, message length, …).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional, Sequence

import numpy as np
from scipy import sparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants and regex helpers
# ---------------------------------------------------------------------------

WILDCARD = "<*>"

# Common log levels we recognise. UNKNOWN is a sentinel for lines without a
# parsable level (we still parse them, just with a coarser feature).
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "FATAL", "CRITICAL", "UNKNOWN")

# Numeric severity used as a numeric feature (higher = more severe).
LOG_LEVEL_SEVERITY = {
    "UNKNOWN":  0,
    "DEBUG":    1,
    "INFO":     2,
    "WARNING":  3,
    "ERROR":    4,
    "FATAL":    5,
    "CRITICAL": 5,
}

# Pre-tokenisation regexes. Order matters — apply IPs before plain numbers.
# Service names in brackets are normalised because the *service* is already
# extracted as a separate structured feature; without this step the tree
# would needlessly fan out one branch per service.
_PREPROCESS_PATTERNS: List[tuple] = [
    (re.compile(r"\[[A-Za-z][\w\-\.]{1,63}\]"),           WILDCARD),  # [service-name]
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), WILDCARD),  # IP[:port]
    (re.compile(r"\b[0-9a-fA-F]{8,}\b"),                  WILDCARD),  # long hex / hashes
    (re.compile(r"\b0x[0-9a-fA-F]+\b"),                   WILDCARD),  # 0x… literals
    (re.compile(r"\bv?\d+(?:\.\d+){1,3}(?:[\-\w]+)?\b"),  WILDCARD),  # versions like v1.2.3
    (re.compile(r"\b\d+(?:\.\d+)?(?:ms|s|m|h|MB|KB|GB|%)\b"), WILDCARD),  # 30s, 4MB, 87%
    (re.compile(r"\b\d+\b"),                              WILDCARD),  # bare integers
]

_LOG_LEVEL_RE  = re.compile(
    r"\b(DEBUG|INFO|WARNING|WARN|ERROR|ERR|FATAL|CRITICAL|CRIT|PANIC|EXCEPTION|TIMEOUT)\b",
    re.IGNORECASE,
)
_SERVICE_RE    = re.compile(r"\[([A-Za-z][\w\-\.]{1,63})\]")
_TIMESTAMP_RES = [
    # ISO 8601 with optional timezone
    re.compile(r"\b(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[\.,]\d+)?(?:Z|[+\-]\d{2}:?\d{2})?)\b"),
    # syslog-style "Jan 02 15:04:05" (assumed current year)
    re.compile(r"\b([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\b"),
]


def _parse_timestamp(line: str) -> Optional[datetime]:
    """Best-effort timestamp extraction. Returns ``None`` if no format matches."""
    for rx in _TIMESTAMP_RES:
        m = rx.search(line)
        if not m:
            continue
        token = m.group(1)
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",   "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",   "%Y-%m-%d %H:%M:%S",
            "%b %d %H:%M:%S",
        ):
            try:
                return datetime.strptime(token.replace("Z", "+0000"), fmt)
            except ValueError:
                continue
    return None


def _extract_level(line: str) -> str:
    m = _LOG_LEVEL_RE.search(line)
    if not m:
        return "UNKNOWN"
    raw = m.group(1).upper()
    # Normalise abbreviations
    if raw in ("WARN",):
        return "WARNING"
    if raw in ("ERR",):
        return "ERROR"
    if raw in ("CRIT",):
        return "CRITICAL"
    if raw in ("PANIC", "EXCEPTION", "TIMEOUT"):
        return "ERROR"  # bucket exotic levels into ERROR for severity scoring
    return raw if raw in LOG_LEVELS else "UNKNOWN"


def _extract_service(line: str) -> Optional[str]:
    m = _SERVICE_RE.search(line)
    return m.group(1) if m else None


def _preprocess(line: str) -> str:
    """Mask common variable patterns *before* tokenisation."""
    out = line
    for rx, repl in _PREPROCESS_PATTERNS:
        out = rx.sub(repl, out)
    return out


def _tokenise(line: str) -> List[str]:
    """Split a (preprocessed) log line into tokens by whitespace."""
    return [t for t in line.strip().split() if t]


def _has_numbers(token: str) -> bool:
    return any(ch.isdigit() for ch in token)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParsedLog:
    """Result of running a single log line through the Drain parser."""
    raw:                  str
    template:             str
    event_id:             str   # short stable hash, e.g. "E1A2"
    parameters:           List[str]
    log_level:            str
    service:              Optional[str]
    timestamp:            Optional[datetime] = None
    timestamp_delta_sec:  Optional[float]    = None

    def to_dict(self) -> dict:
        return {
            "raw":                 self.raw,
            "template":            self.template,
            "event_id":            self.event_id,
            "parameters":          list(self.parameters),
            "log_level":           self.log_level,
            "service":             self.service,
            "timestamp":           self.timestamp.isoformat() if self.timestamp else None,
            "timestamp_delta_sec": self.timestamp_delta_sec,
        }


@dataclass
class _LogCluster:
    """One cluster (a.k.a. log template group) inside the Drain tree."""
    cluster_id:    int
    template:      List[str]   # tokens, may contain WILDCARD
    log_count:     int = 0
    example_lines: List[str] = field(default_factory=list)

    def template_str(self) -> str:
        return " ".join(self.template)


class _Node:
    """Internal-tree node. Children may be inner nodes or a list of clusters."""
    __slots__ = ("children", "clusters")

    def __init__(self) -> None:
        self.children: dict = {}
        self.clusters: List[_LogCluster] = []


# ---------------------------------------------------------------------------
# Drain parser
# ---------------------------------------------------------------------------

class DrainLogParser:
    """
    Online log-template miner using a fixed-depth parse tree.

    Parameters
    ----------
    depth : int
        Maximum tree depth (root + token layers). Following the original
        paper, ``depth=4`` gives one length-layer + two token-layers + leaves.
    sim_threshold : float
        Minimum similarity (matching token ratio) to merge an incoming line
        into an existing cluster. Range: 0–1, typical 0.4.
    max_children : int
        Maximum number of distinct token branches at any internal node before
        the parser falls back to a wildcard branch (controls tree fan-out).
    """

    def __init__(
        self,
        depth:         int   = 4,
        sim_threshold: float = 0.4,
        max_children:  int   = 100,
    ) -> None:
        if depth < 3:
            raise ValueError("depth must be >= 3 (length + 1 token + leaves)")
        self.depth         = depth
        self.sim_threshold = sim_threshold
        self.max_children  = max_children

        self._root: _Node                = _Node()
        self._clusters: List[_LogCluster] = []
        self._next_id: int               = 0

    # ----- public API ----------------------------------------------------

    @property
    def n_clusters(self) -> int:
        return len(self._clusters)

    def parse_line(self, line: str) -> ParsedLog:
        """
        Parse a single line and update the tree in place.

        Returns a populated :class:`ParsedLog`.
        """
        line = line if line is not None else ""
        level     = _extract_level(line)
        service   = _extract_service(line)
        timestamp = _parse_timestamp(line)

        masked = _preprocess(line)
        tokens = _tokenise(masked)

        cluster = self._match_or_insert(tokens, line)
        params  = self._extract_parameters(cluster.template, tokens)

        return ParsedLog(
            raw        = line,
            template   = cluster.template_str(),
            event_id   = self._event_id(cluster),
            parameters = params,
            log_level  = level,
            service    = service,
            timestamp  = timestamp,
        )

    def parse_batch(self, lines: Sequence[str]) -> List[ParsedLog]:
        """
        Parse multiple lines, computing ``timestamp_delta_sec`` between
        consecutive lines that have parsable timestamps.
        """
        parsed: List[ParsedLog] = []
        prev_ts: Optional[datetime] = None
        for line in lines:
            p = self.parse_line(line)
            if p.timestamp is not None and prev_ts is not None:
                p.timestamp_delta_sec = (p.timestamp - prev_ts).total_seconds()
            if p.timestamp is not None:
                prev_ts = p.timestamp
            parsed.append(p)
        return parsed

    def get_clusters(self, top_k: Optional[int] = None) -> List[dict]:
        """
        Return cluster summaries sorted by ``log_count`` descending. Useful
        for /api/analytics/log-templates and for thesis reporting.
        """
        rows = sorted(self._clusters, key=lambda c: c.log_count, reverse=True)
        if top_k is not None:
            rows = rows[:top_k]
        return [
            {
                "event_id":  self._event_id(c),
                "template":  c.template_str(),
                "count":     c.log_count,
                "examples":  list(c.example_lines[:3]),
            }
            for c in rows
        ]

    # ----- internal: tree traversal -------------------------------------

    def _match_or_insert(self, tokens: List[str], raw: str) -> _LogCluster:
        if not tokens:
            # empty line → dedicated cluster keyed off length 0
            tokens = [WILDCARD]

        length     = len(tokens)
        len_node   = self._root.children.get(length)
        if len_node is None:
            len_node = _Node()
            self._root.children[length] = len_node

        cur_node, cur_depth = len_node, 1
        max_token_depth = min(self.depth - 2, length)
        # Walk down by tokens (use wildcard-branch when token has digits or fan-out is full).
        while cur_depth <= max_token_depth:
            tok = tokens[cur_depth - 1]
            key = WILDCARD if _has_numbers(tok) else tok

            child = cur_node.children.get(key)
            if child is None:
                if len(cur_node.children) >= self.max_children:
                    # bucket-overflow: collapse to wildcard branch
                    child = cur_node.children.get(WILDCARD)
                    if child is None:
                        child = _Node()
                        cur_node.children[WILDCARD] = child
                else:
                    child = _Node()
                    cur_node.children[key] = child
            cur_node = child
            cur_depth += 1

        # ----- leaf matching -----
        best_cluster, best_sim, best_param_count = None, -1.0, -1
        for cluster in cur_node.clusters:
            if len(cluster.template) != length:
                continue
            sim, param_count = self._seq_distance(cluster.template, tokens)
            # tie-break by larger #params (Drain heuristic)
            if sim > best_sim or (sim == best_sim and param_count > best_param_count):
                best_sim, best_cluster, best_param_count = sim, cluster, param_count

        if best_cluster is not None and best_sim >= self.sim_threshold:
            self._update_template(best_cluster, tokens, raw)
            return best_cluster

        new_cluster = _LogCluster(
            cluster_id   = self._next_id,
            template     = list(tokens),
            log_count    = 1,
            example_lines= [raw],
        )
        self._next_id += 1
        cur_node.clusters.append(new_cluster)
        self._clusters.append(new_cluster)
        return new_cluster

    @staticmethod
    def _seq_distance(template: List[str], seq: List[str]) -> tuple:
        """Drain similarity: matching non-wildcard positions / total length."""
        if len(template) != len(seq):
            return -1.0, 0
        sim_tokens  = 0
        param_count = 0
        for t, s in zip(template, seq):
            if t == WILDCARD:
                param_count += 1
                continue
            if t == s:
                sim_tokens += 1
        sim = sim_tokens / float(len(seq))
        return sim, param_count

    @staticmethod
    def _update_template(cluster: _LogCluster, seq: List[str], raw: str) -> None:
        """Generalise the template wherever the new sequence differs."""
        new_template = []
        changed = False
        for t, s in zip(cluster.template, seq):
            if t == s:
                new_template.append(t)
            else:
                if t != WILDCARD:
                    changed = True
                new_template.append(WILDCARD)
        if changed:
            cluster.template = new_template
        cluster.log_count += 1
        if len(cluster.example_lines) < 3:
            cluster.example_lines.append(raw)

    @staticmethod
    def _extract_parameters(template: List[str], seq: List[str]) -> List[str]:
        """Return concrete tokens that fall on wildcard positions."""
        if len(template) != len(seq):
            return []
        return [s for t, s in zip(template, seq) if t == WILDCARD and s != WILDCARD]

    @staticmethod
    def _event_id(cluster: _LogCluster) -> str:
        """
        Short, stable id derived from the cluster id (NOT the template string).

        Using ``cluster_id`` is critical: a template can be *generalised* over
        time (more positions becoming wildcards), so a hash of the template
        string would silently shift event ids and confuse the featurizer.
        """
        return f"E{cluster.cluster_id:05d}"


# ---------------------------------------------------------------------------
# Featurizer — turns parsed events into sparse ML features
# ---------------------------------------------------------------------------

class StructuredLogFeaturizer:
    """
    Convert raw log lines into a sparse feature matrix using Drain templates.

    Feature layout (column order matters — kept stable for SHAP):
        [ template one-hot (top-K + OTHER) ]
        [ log-level one-hot (7 levels)     ]
        [ service one-hot (top-S + OTHER)  ]
        [ numeric: severity, msg_len, n_params, has_timestamp ]

    The featurizer is fully picklable so it ships inside the trained model
    bundle and is loaded automatically at inference time.
    """

    NUMERIC_FEATURES = ("level_severity", "msg_length", "num_params", "has_timestamp")

    def __init__(
        self,
        top_templates: int = 200,
        top_services:  int = 32,
        sim_threshold: float = 0.4,
        depth:         int = 4,
    ) -> None:
        self.top_templates = top_templates
        self.top_services  = top_services
        self.parser = DrainLogParser(depth=depth, sim_threshold=sim_threshold)

        # Populated at fit():
        self._template_index: dict = {}   # event_id -> column index
        self._service_index:  dict = {}   # service  -> column index
        self._level_index:    dict = {lvl: i for i, lvl in enumerate(LOG_LEVELS)}
        self._n_features:     int  = 0
        self.is_fitted:       bool = False

    # ----- shapes -------------------------------------------------------

    @property
    def feature_names(self) -> List[str]:
        names: List[str] = []
        for tmpl_id in self._template_index:
            names.append(f"tmpl::{tmpl_id}")
        for svc in self._service_index:
            names.append(f"svc::{svc}")
        for lvl in LOG_LEVELS:
            names.append(f"lvl::{lvl}")
        names.extend(f"num::{n}" for n in self.NUMERIC_FEATURES)
        return names

    def n_features(self) -> int:
        return self._n_features

    # ----- fit / transform ---------------------------------------------

    def fit(self, lines: Sequence[str]) -> "StructuredLogFeaturizer":
        """Discover templates and most-common services from the training corpus."""
        parsed = self.parser.parse_batch(list(lines))

        # --- template index: top-K by frequency, tail bucket = OTHER ---
        cluster_counts = sorted(
            self.parser.get_clusters(),
            key=lambda r: r["count"],
            reverse=True,
        )
        kept = cluster_counts[: self.top_templates]
        self._template_index = {row["event_id"]: i for i, row in enumerate(kept)}
        self._template_index["__OTHER__"] = len(self._template_index)

        # --- service index: top-S, tail bucket = OTHER ---
        from collections import Counter
        svc_counts = Counter(p.service or "__NONE__" for p in parsed)
        top_svc = [s for s, _ in svc_counts.most_common(self.top_services)]
        self._service_index = {svc: i for i, svc in enumerate(top_svc)}
        if "__OTHER__" not in self._service_index:
            self._service_index["__OTHER__"] = len(self._service_index)

        self._n_features = (
            len(self._template_index)
            + len(self._service_index)
            + len(LOG_LEVELS)
            + len(self.NUMERIC_FEATURES)
        )
        self.is_fitted = True
        logger.info(
            "StructuredLogFeaturizer fitted: %d clusters, %d service slots, %d features",
            self.parser.n_clusters, len(self._service_index), self._n_features,
        )
        return self

    def transform(self, lines: Sequence[str]) -> sparse.csr_matrix:
        """Vectorise lines using the fitted parser. Inserts new lines into the
        live tree so streaming logs benefit from continued learning, but the
        feature *space* is fixed (unseen templates → OTHER bucket)."""
        if not self.is_fitted:
            raise RuntimeError("StructuredLogFeaturizer.transform called before fit().")

        parsed = self.parser.parse_batch(list(lines))
        return self._encode(parsed)

    def fit_transform(self, lines: Sequence[str]) -> sparse.csr_matrix:
        # Slightly more efficient: we already parsed during fit().
        self.fit(lines)
        parsed = self.parser.parse_batch(list(lines))
        return self._encode(parsed)

    def transform_parsed(self, parsed: Iterable[ParsedLog]) -> sparse.csr_matrix:
        """Encode pre-parsed logs (skips re-running Drain)."""
        if not self.is_fitted:
            raise RuntimeError("StructuredLogFeaturizer.transform_parsed called before fit().")
        return self._encode(list(parsed))

    # ----- encoding -----------------------------------------------------

    def _encode(self, parsed: List[ParsedLog]) -> sparse.csr_matrix:
        n     = len(parsed)
        rows  = []
        cols  = []
        data  = []

        tmpl_offset    = 0
        svc_offset     = tmpl_offset + len(self._template_index)
        level_offset   = svc_offset  + len(self._service_index)
        numeric_offset = level_offset + len(LOG_LEVELS)

        other_tmpl_col = tmpl_offset + self._template_index["__OTHER__"]
        other_svc_col  = svc_offset  + self._service_index["__OTHER__"]

        for i, p in enumerate(parsed):
            # template one-hot
            tcol = self._template_index.get(p.event_id)
            cols.append(tmpl_offset + tcol if tcol is not None else other_tmpl_col)
            rows.append(i); data.append(1.0)

            # service one-hot
            svc_key = p.service if p.service in self._service_index else "__OTHER__"
            cols.append(svc_offset + self._service_index[svc_key])
            rows.append(i); data.append(1.0)

            # level one-hot
            lvl = p.log_level if p.log_level in self._level_index else "UNKNOWN"
            cols.append(level_offset + self._level_index[lvl])
            rows.append(i); data.append(1.0)

            # numeric features
            severity = LOG_LEVEL_SEVERITY.get(p.log_level, 0) / 5.0  # 0-1
            msg_len  = min(len(p.raw), 500) / 500.0                  # 0-1
            n_params = min(len(p.parameters), 20) / 20.0             # 0-1
            has_ts   = 1.0 if p.timestamp is not None else 0.0

            for j, val in enumerate((severity, msg_len, n_params, has_ts)):
                if val:
                    rows.append(i); cols.append(numeric_offset + j); data.append(val)

        return sparse.csr_matrix(
            (data, (rows, cols)), shape=(n, self._n_features), dtype=np.float32,
        )


__all__ = [
    "DrainLogParser",
    "ParsedLog",
    "StructuredLogFeaturizer",
    "LOG_LEVELS",
    "LOG_LEVEL_SEVERITY",
    "WILDCARD",
]
