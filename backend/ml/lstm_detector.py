"""
LSTM sequence classifier for CI/CD build failure prediction.

Architecture:
  Token IDs  →  Embedding  →  mean-pool per line  →  2-layer biLSTM  →  Linear head

Each "sample" is a *sequence* of SEQ_LEN log lines that represent one build.
The model learns temporal patterns — e.g. a build that starts normally but
accumulates warnings before crashing is caught by the LSTM whereas a
single-line classifier would miss it.
"""

import os
import re
import logging
from typing import List, Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Optional PyTorch import ────────────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    import torch.optim as optim
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    logger.warning("PyTorch not installed. LSTMLogDetector will be disabled.")

# ── Hyper-parameters ───────────────────────────────────────────────────────────
SEQ_LEN    = 20    # log lines per build sequence
MAX_TOKENS = 30    # tokens per line (pad / truncate)
EMBED_DIM  = 64
HIDDEN_DIM = 128
NUM_LAYERS = 2
DROPOUT    = 0.3
BATCH_SIZE = 64
EPOCHS     = 15
LR         = 1e-3
MIN_SEQS   = 50    # minimum sequences before training is attempted

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "lstm_classifier.pt",
)

# ── Tokenisation (mirrors the TF-IDF pipeline in anomaly.py) ──────────────────
_IP_RE  = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b")
_HEX_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
_NUM_RE = re.compile(r"\b\d+\.?\d*\b")
_TOK_RE = re.compile(r"[a-z<>]+")

def _tokenize_line(text: str) -> List[str]:
    t = text.lower()
    t = _IP_RE.sub("<ip>", t)
    t = _HEX_RE.sub("<hex>", t)
    t = _NUM_RE.sub("<num>", t)
    return _TOK_RE.findall(t)


# ── Vocabulary ─────────────────────────────────────────────────────────────────
PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"


class SimpleVocab:
    """Minimal token-to-integer vocabulary built from training sequences."""

    def __init__(self, min_freq: int = 1):
        self.min_freq  = min_freq
        self.token2id: Dict[str, int] = {PAD_TOKEN: 0, UNK_TOKEN: 1}
        self.id2token: Dict[int, str] = {0: PAD_TOKEN, 1: UNK_TOKEN}

    def build(self, tokenised_builds: List[List[List[str]]]) -> None:
        """
        tokenised_builds: list of builds,
        each build = list of lines, each line = list of token strings.
        """
        from collections import Counter
        freq: Counter = Counter()
        for build in tokenised_builds:
            for line_tokens in build:
                freq.update(line_tokens)
        for tok, cnt in freq.items():
            if cnt >= self.min_freq and tok not in self.token2id:
                idx = len(self.token2id)
                self.token2id[tok] = idx
                self.id2token[idx] = tok

    def encode(self, tokens: List[str]) -> List[int]:
        unk = self.token2id[UNK_TOKEN]
        return [self.token2id.get(t, unk) for t in tokens]

    def __len__(self) -> int:
        return len(self.token2id)


# ── Dataset ────────────────────────────────────────────────────────────────────
if _TORCH_AVAILABLE:
    class BuildSequenceDataset(Dataset):
        """
        Each sample is a (SEQ_LEN, MAX_TOKENS) int64 tensor + float label.
        """

        def __init__(
            self,
            tokenised_builds: List[List[List[str]]],
            labels: List[int],
            vocab: SimpleVocab,
        ):
            self.vocab  = vocab
            self.labels = labels
            self.data   = [self._encode_build(b) for b in tokenised_builds]

        def _encode_build(self, build: List[List[str]]):
            lines = build[:SEQ_LEN]
            while len(lines) < SEQ_LEN:
                lines.append([])                 # pad with empty line
            encoded = []
            for line_tokens in lines:
                ids = self.vocab.encode(line_tokens)[:MAX_TOKENS]
                ids += [0] * (MAX_TOKENS - len(ids))  # pad to MAX_TOKENS
                encoded.append(ids)
            return torch.tensor(encoded, dtype=torch.long)  # (SEQ_LEN, MAX_TOKENS)

        def __len__(self) -> int:
            return len(self.data)

        def __getitem__(self, idx):
            return self.data[idx], torch.tensor(self.labels[idx], dtype=torch.float32)


# ── Neural network ─────────────────────────────────────────────────────────────
if _TORCH_AVAILABLE:
    class _LSTMNet(nn.Module):
        """
        Embedding → mean-pool over tokens per line → biLSTM → linear head.

        Input  : (batch, SEQ_LEN, MAX_TOKENS)  int64 token IDs
        Output : (batch,)  sigmoid probability of build failure
        """

        def __init__(self, vocab_size: int):
            super().__init__()
            self.embedding = nn.Embedding(vocab_size, EMBED_DIM, padding_idx=0)
            self.lstm = nn.LSTM(
                EMBED_DIM, HIDDEN_DIM,
                num_layers=NUM_LAYERS,
                batch_first=True,
                dropout=DROPOUT if NUM_LAYERS > 1 else 0.0,
                bidirectional=True,
            )
            self.dropout = nn.Dropout(DROPOUT)
            # bidirectional → hidden size doubles
            self.head = nn.Linear(HIDDEN_DIM * 2, 1)

        def forward(self, x):
            # x : (batch, SEQ_LEN, MAX_TOKENS)
            emb      = self.embedding(x)          # (B, S, T, E)
            line_emb = emb.mean(dim=2)            # (B, S, E)  mean-pool tokens
            _, (h_n, _) = self.lstm(line_emb)     # h_n: (num_layers*2, B, H)
            h_fwd = h_n[-2]                       # last forward  layer output
            h_bwd = h_n[-1]                       # last backward layer output
            h     = torch.cat([h_fwd, h_bwd], dim=1)  # (B, H*2)
            h     = self.dropout(h)
            return torch.sigmoid(self.head(h).squeeze(1))  # (B,)


# ── Public API ─────────────────────────────────────────────────────────────────

class LSTMLogDetector:
    """
    Sequence-level CI/CD build failure detector.

    Input  : a list of SEQ_LEN log-line strings representing one build.
    Output : failure probability in [0, 1].

    Unlike single-line classifiers (LR / RF / XGBoost), this model captures
    temporal context — it sees how the build *evolves* over its log stream.
    """

    def __init__(self):
        self.vocab:         SimpleVocab | None  = None
        self.model:         "_LSTMNet | None"   = None
        self.is_trained:    bool                = False
        self.epoch_metrics: List[Dict]          = []

    # ── training ──────────────────────────────────────────────────────────────

    def train(
        self,
        sequences: List[List[str]],   # each element = list of log-line strings
        labels:    List[int],          # 1 = build failed, 0 = build succeeded
        epochs:    int = EPOCHS,
    ) -> List[Dict]:
        """
        Train the LSTM on labeled build sequences.

        Returns a list of per-epoch metric dicts with keys:
          epoch, train_loss, val_loss, accuracy, f1_score, learning_rate
        These are saved to TrainingHistory to produce real learning curves.
        """
        if not _TORCH_AVAILABLE:
            logger.error("PyTorch not installed — LSTM training skipped.")
            return []

        if len(sequences) < MIN_SEQS:
            logger.warning(
                f"Need >= {MIN_SEQS} build sequences; got {len(sequences)}. Skipping."
            )
            return []

        logger.info(f"Tokenising {len(sequences)} build sequences ...")
        tokenised = [[_tokenize_line(line) for line in seq] for seq in sequences]

        # Build vocabulary from training data
        self.vocab = SimpleVocab(min_freq=1)
        self.vocab.build(tokenised)
        logger.info(f"Vocabulary size: {len(self.vocab)} tokens")

        # 80 / 20 stratified split
        from sklearn.model_selection import train_test_split
        tok_tr, tok_val, y_tr, y_val = train_test_split(
            tokenised, labels,
            test_size=0.2, random_state=42, stratify=labels,
        )

        ds_train = BuildSequenceDataset(tok_tr, y_tr, self.vocab)
        ds_val   = BuildSequenceDataset(tok_val, y_val, self.vocab)
        dl_train = DataLoader(ds_train, batch_size=BATCH_SIZE, shuffle=True)
        dl_val   = DataLoader(ds_val,   batch_size=BATCH_SIZE)

        self.model = _LSTMNet(vocab_size=len(self.vocab))
        criterion  = nn.BCELoss()
        optimizer  = optim.Adam(self.model.parameters(), lr=LR)
        scheduler  = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

        epoch_metrics = []
        logger.info(f"Training LSTM for {epochs} epochs ...")

        for ep in range(1, epochs + 1):
            self.model.train()
            total_loss = 0.0
            for xb, yb in dl_train:
                optimizer.zero_grad()
                pred = self.model(xb)
                loss = criterion(pred, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item() * len(yb)

            current_lr = scheduler.get_last_lr()[0]
            scheduler.step()

            train_loss = total_loss / len(ds_train)
            val_loss, acc, f1 = self._eval_loop(dl_val, criterion, len(ds_val))

            logger.info(
                f"  Epoch {ep:02d}/{epochs}  "
                f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  "
                f"acc={acc:.4f}  f1={f1:.4f}"
            )
            epoch_metrics.append({
                "epoch":        ep,
                "train_loss":   train_loss,
                "val_loss":     val_loss,
                "accuracy":     acc,
                "f1_score":     f1,
                "learning_rate": current_lr,
            })

        self.is_trained    = True
        self.epoch_metrics = epoch_metrics
        self._save()
        return epoch_metrics

    # ── evaluation ────────────────────────────────────────────────────────────

    def _eval_loop(
        self,
        dl: "DataLoader",
        criterion: "nn.BCELoss",
        n_samples: int,
    ) -> Tuple[float, float, float]:
        from sklearn.metrics import f1_score, accuracy_score
        self.model.eval()
        total_loss, y_true, y_pred = 0.0, [], []
        with torch.no_grad():
            for xb, yb in dl:
                prob = self.model(xb)
                total_loss += criterion(prob, yb).item() * len(yb)
                y_pred.extend((prob >= 0.5).int().tolist())
                y_true.extend(yb.int().tolist())
        avg_loss = total_loss / n_samples
        acc = float(accuracy_score(y_true, y_pred))
        f1  = float(f1_score(y_true, y_pred, zero_division=0))
        return avg_loss, acc, f1

    def evaluate(self, sequences: List[List[str]], labels: List[int]) -> Dict:
        """
        Compute held-out metrics on a separate test set.
        Returns the same keys as SupervisedLogClassifier.evaluate_on_test()
        so it can be inserted into MultiModelMetrics with identical schema.
        """
        if not self.is_trained or not _TORCH_AVAILABLE:
            return {}
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score,
            f1_score, roc_auc_score, confusion_matrix,
        )
        tokenised = [[_tokenize_line(l) for l in seq] for seq in sequences]
        ds = BuildSequenceDataset(tokenised, labels, self.vocab)
        dl = DataLoader(ds, batch_size=BATCH_SIZE)

        self.model.eval()
        y_true, y_pred, y_prob = [], [], []
        with torch.no_grad():
            for xb, yb in dl:
                prob = self.model(xb)
                y_prob.extend(prob.tolist())
                y_pred.extend((prob >= 0.5).int().tolist())
                y_true.extend(yb.int().tolist())

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        return {
            "accuracy":  float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall":    float(recall_score(y_true, y_pred, zero_division=0)),
            "f1_score":  float(f1_score(y_true, y_pred, zero_division=0)),
            "roc_auc":   float(roc_auc_score(y_true, y_prob)),
            "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
        }

    def predict(self, lines: List[str]) -> Dict:
        """
        Predict failure probability for a single build.

        lines: list of log-line strings (ideally SEQ_LEN lines).
        Returns dict with failure_probability, is_failure, confidence, model.
        """
        if not self.is_trained or not _TORCH_AVAILABLE:
            return {
                "failure_probability": 0.0,
                "is_failure":          False,
                "confidence":          0.5,
                "model":               "lstm_disabled",
            }
        tokenised = [[_tokenize_line(l) for l in lines]]
        ds = BuildSequenceDataset(tokenised, [0], self.vocab)
        xb, _ = ds[0]
        self.model.eval()
        with torch.no_grad():
            prob = float(self.model(xb.unsqueeze(0)).item())
        return {
            "failure_probability": prob,
            "is_failure":          prob >= 0.5,
            "confidence":          max(prob, 1.0 - prob),
            "model":               "lstm",
        }

    # ── persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        payload = {
            "vocab":         self.vocab,
            "model_state":   self.model.state_dict(),
            "epoch_metrics": self.epoch_metrics,
            "vocab_size":    len(self.vocab),
        }
        torch.save(payload, MODEL_PATH)
        logger.info(f"LSTM model saved → {MODEL_PATH}")

    def load_model(self) -> bool:
        if not _TORCH_AVAILABLE or not os.path.exists(MODEL_PATH):
            return False
        try:
            payload = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
            self.vocab  = payload["vocab"]
            self.model  = _LSTMNet(vocab_size=payload["vocab_size"])
            self.model.load_state_dict(payload["model_state"])
            self.model.eval()
            self.epoch_metrics = payload.get("epoch_metrics", [])
            self.is_trained    = True
            logger.info("LSTM model loaded from disk.")
            return True
        except Exception as exc:
            logger.warning(f"Could not load LSTM model: {exc}")
            return False
