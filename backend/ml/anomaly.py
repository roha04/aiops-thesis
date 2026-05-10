"""
Log Anomaly Detection — Supervised TF-IDF + Drain + Multi-Classifier Pipeline

Models    : Logistic Regression, Random Forest, XGBoost
Features  : TF-IDF tokens **horizontally stacked** with structured features
            mined by Drain (event template id, log level, service name,
            parameter count, message length, etc.). See ``ml/log_parser.py``.
Evaluation: 5-fold stratified cross-validation
Inference : best model (by CV F1) used at prediction time
"""

import re
import os
import pickle
import logging

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
)

from ml.log_parser import StructuredLogFeaturizer

try:
    from xgboost import XGBClassifier
    _XGBOOST = True
except ImportError:
    _XGBOOST = False

try:
    import shap
    _SHAP = True
except ImportError:
    _SHAP = False

logger = logging.getLogger(__name__)

MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> str:
    """Normalise a single log line for TF-IDF vectorisation."""
    t = text.lower()
    # mask IP addresses, hex values, numbers so they don't fragment vocabulary
    t = re.sub(r"\d{1,3}(?:\.\d{1,3}){3}", "<ip>", t)
    t = re.sub(r"0x[0-9a-f]+", "<hex>", t)
    t = re.sub(r"\b\d+\b", "<num>", t)
    tokens = re.findall(r"[a-z]+(?:_[a-z]+)*|<ip>|<hex>|<num>", t)
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# Classifier factory
# ---------------------------------------------------------------------------

def _build_classifiers() -> dict:
    clfs = {
        "Logistic Regression": LogisticRegression(
            C=1.0, max_iter=1000, class_weight="balanced", random_state=42
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=None, class_weight="balanced",
            random_state=42, n_jobs=-1,
        ),
    }
    if _XGBOOST:
        clfs["XGBoost"] = XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            scale_pos_weight=1, eval_metric="logloss",
            random_state=42, verbosity=0,
        )
    else:
        # Gradient Boosting as XGBoost fallback
        clfs["XGBoost"] = GradientBoostingClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42,
        )
    return clfs


# ---------------------------------------------------------------------------
# Main classifier class
# ---------------------------------------------------------------------------

class SupervisedLogClassifier:
    """
    Supervised log anomaly classifier.

    Trains Logistic Regression, Random Forest, and XGBoost on a hybrid
    feature representation — TF-IDF tokens stacked with Drain-derived
    structured features (template id, log level, service, message length,
    parameter count) — using 5-fold stratified cross-validation. The best
    model is retained for real-time inference.

    Parameters
    ----------
    use_drain_features : bool, default True
        When True, the classifier consumes ``hstack(TF-IDF, structured)``.
        When False, only TF-IDF is used (legacy / ablation mode).
    """

    def __init__(self, use_drain_features: bool = True):
        self.vectorizer = TfidfVectorizer(
            preprocessor=_tokenize,
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
        )
        self.use_drain_features = use_drain_features
        self.structured_featurizer: StructuredLogFeaturizer | None = (
            StructuredLogFeaturizer() if use_drain_features else None
        )
        self.classifiers: dict = {}
        self.best_model_name: str = "Random Forest"
        self.cv_results: dict = {}
        self.test_metrics: dict = {}
        self.feature_names: list = []   # TF-IDF names + structured names
        self.is_trained: bool = False
        # Lazily-built SHAP TreeExplainer wrapping the trained Random Forest.
        # Built on first call to .explain() so training cost is unaffected.
        self._explainer = None

    # ----- feature assembly -------------------------------------------------

    def _build_features(self, logs: list, fit: bool):
        """
        Return a sparse feature matrix for the given log lines.

        ``fit=True`` re-fits TF-IDF and the structured featurizer (used during
        ``train``); ``fit=False`` uses the already-fitted vectorisers.
        """
        if fit:
            X_tfidf = self.vectorizer.fit_transform([_tokenize(l) for l in logs])
        else:
            X_tfidf = self.vectorizer.transform([_tokenize(l) for l in logs])

        if not self.use_drain_features or self.structured_featurizer is None:
            return X_tfidf

        if fit:
            X_struct = self.structured_featurizer.fit_transform(list(logs))
        else:
            X_struct = self.structured_featurizer.transform(list(logs))

        return sparse.hstack([X_tfidf, X_struct], format="csr")

    def _refresh_feature_names(self) -> None:
        """Rebuild the ordered ``feature_names`` list (TF-IDF + structured)."""
        names = self.vectorizer.get_feature_names_out().tolist()
        if self.use_drain_features and self.structured_featurizer is not None:
            names = names + self.structured_featurizer.feature_names
        self.feature_names = names

    # ----- training --------------------------------------------------------

    def train(self, logs: list, labels: list) -> dict:
        """
        Fit TF-IDF + Drain featurizer + all classifiers with 5-fold CV,
        then retrain on the full set. Returns per-model CV metrics dict.
        """
        if len(logs) < 50:
            logger.warning("Need at least 50 samples; skipping training.")
            return {}

        logger.info(f"Fitting feature pipeline on {len(logs)} samples ...")
        X = self._build_features(logs, fit=True)
        y = np.array(labels)
        self._refresh_feature_names()
        if self.use_drain_features and self.structured_featurizer is not None:
            logger.info(
                "  TF-IDF features: %d, Drain templates discovered: %d",
                len(self.vectorizer.get_feature_names_out()),
                self.structured_featurizer.parser.n_clusters,
            )

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        clfs = _build_classifiers()
        cv_results = {}

        for name, clf in clfs.items():
            logger.info(f"  [{name}] 5-fold CV ...")
            scores = cross_validate(
                clf, X, y, cv=cv,
                scoring=["f1", "precision", "recall", "accuracy"],
                return_train_score=False, n_jobs=-1,
            )
            # Retrain on ALL training data for inference
            clf.fit(X, y)
            self.classifiers[name] = clf

            cv_results[name] = {
                "cv_f1_mean":        float(scores["test_f1"].mean()),
                "cv_f1_std":         float(scores["test_f1"].std()),
                "cv_precision_mean": float(scores["test_precision"].mean()),
                "cv_recall_mean":    float(scores["test_recall"].mean()),
                "cv_accuracy_mean":  float(scores["test_accuracy"].mean()),
            }
            logger.info(
                f"    CV F1 = {cv_results[name]['cv_f1_mean']:.4f}"
                f" +/- {cv_results[name]['cv_f1_std']:.4f}"
            )

        self.cv_results = cv_results
        self.best_model_name = max(
            cv_results, key=lambda k: cv_results[k]["cv_f1_mean"]
        )
        logger.info(
            f"Best model: {self.best_model_name} "
            f"(CV F1 = {cv_results[self.best_model_name]['cv_f1_mean']:.4f})"
        )
        self.is_trained = True
        # New RF -> invalidate cached SHAP explainer so it is rebuilt on demand.
        self._explainer = None
        self._save()
        return cv_results

    # ----- evaluation ------------------------------------------------------

    def evaluate_on_test(self, logs: list, labels: list) -> dict:
        """Compute held-out test metrics for every trained classifier."""
        if not self.is_trained:
            return {}
        X = self._build_features(logs, fit=False)
        y = np.array(labels)
        metrics = {}
        for name, clf in self.classifiers.items():
            y_pred = clf.predict(X)
            y_prob = clf.predict_proba(X)[:, 1]
            tn, fp, fn, tp = confusion_matrix(y, y_pred).ravel()
            metrics[name] = {
                "accuracy":  float(accuracy_score(y, y_pred)),
                "precision": float(precision_score(y, y_pred, zero_division=0)),
                "recall":    float(recall_score(y, y_pred, zero_division=0)),
                "f1_score":  float(f1_score(y, y_pred, zero_division=0)),
                "roc_auc":   float(roc_auc_score(y, y_prob)),
                "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn),
            }
        self.test_metrics = metrics
        return metrics

    # ----- feature importance ----------------------------------------------

    def get_feature_importance(self, top_n: int = 20) -> dict:
        """Real feature importance from the trained Random Forest model."""
        clf = self.classifiers.get("Random Forest")
        if clf is None or not hasattr(clf, "feature_importances_"):
            return {}
        importances = clf.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]
        return {
            "features":   [self.feature_names[i] for i in indices],
            "importance": [float(importances[i]) for i in indices],
        }

    # ----- SHAP explainability (per-prediction) ----------------------------

    def _ensure_explainer(self):
        """Lazily build a SHAP TreeExplainer around the trained RF model."""
        if self._explainer is not None:
            return self._explainer
        if not _SHAP:
            return None
        rf = self.classifiers.get("Random Forest")
        if rf is None:
            return None
        try:
            self._explainer = shap.TreeExplainer(rf)
            return self._explainer
        except Exception as exc:
            logger.warning(f"Could not build SHAP TreeExplainer: {exc}")
            return None

    @staticmethod
    def _normalise_shap_output(sv, n_features: int) -> np.ndarray:
        """
        SHAP returns different shapes depending on version / model:
          * list[ndarray]            (legacy binary classifier)
          * ndarray (n, f, n_classes)  (modern multi-output)
          * ndarray (n, f)             (already collapsed)
        We always extract class-1 ("anomaly") SHAP values for one sample.
        """
        if isinstance(sv, list):
            arr = sv[1] if len(sv) > 1 else sv[0]
            return np.asarray(arr[0])
        sv = np.asarray(sv)
        if sv.ndim == 3:
            return sv[0, :, 1] if sv.shape[2] > 1 else sv[0, :, 0]
        if sv.ndim == 2:
            return sv[0]
        # 1-D (single feature vector) — shouldn't happen but handle gracefully
        return sv.reshape(-1)[:n_features]

    def explain(self, log_text: str, top_k: int = 3) -> dict:
        """
        Compute the top-K features that drove a prediction, using SHAP values
        from the trained Random Forest. Positive SHAP value -> push toward
        anomaly; negative -> pull toward normal.

        Returns:
            {
                "model": "Random Forest",
                "base_value": float,           # explainer expected value (anomaly class)
                "features": [
                    {"feature": str, "shap_value": float,
                     "direction": "anomaly" | "normal", "tfidf": float},
                    ...
                ],
            }
        Empty dict if SHAP is unavailable or the model isn't trained.
        """
        if not self.is_trained or not _SHAP:
            return {}

        explainer = self._ensure_explainer()
        if explainer is None:
            return {}

        try:
            x_sparse = self._build_features([log_text], fit=False)
            x_dense = x_sparse.toarray()
            sv = explainer.shap_values(x_dense)
            shap_vals = self._normalise_shap_output(sv, n_features=x_dense.shape[1])

            # Base value (E[f(x)] for the anomaly class)
            base = explainer.expected_value
            if isinstance(base, (list, np.ndarray)):
                base_arr = np.asarray(base).reshape(-1)
                base_val = float(base_arr[1] if base_arr.size > 1 else base_arr[0])
            else:
                base_val = float(base)

            # Restrict to features actually present in this log line so the
            # explanation stays human-readable. If the log has fewer than
            # top_k tokens we fall back to the global top-|shap| features.
            tfidf_row = x_dense[0]
            present_idx = np.where(tfidf_row > 0)[0]
            candidates = present_idx if present_idx.size >= top_k else np.arange(len(shap_vals))

            ranked = sorted(
                candidates,
                key=lambda i: abs(float(shap_vals[i])),
                reverse=True,
            )[:top_k]

            features = []
            for i in ranked:
                sv_i = float(shap_vals[i])
                features.append({
                    "feature":    self.feature_names[i] if i < len(self.feature_names) else f"f{i}",
                    "shap_value": sv_i,
                    "direction":  "anomaly" if sv_i >= 0 else "normal",
                    "tfidf":      float(tfidf_row[i]),
                })

            return {
                "model":      "Random Forest",
                "base_value": base_val,
                "features":   features,
            }
        except Exception as exc:
            logger.error(f"SHAP explain error: {exc}")
            return {}

    # ----- predict (uses best model at inference time) ---------------------

    def predict(self, log_text: str) -> dict:
        """Single-sample prediction using the best trained classifier."""
        if not self.is_trained:
            return self._keyword_fallback(log_text)
        try:
            X = self._build_features([log_text], fit=False)
            clf = self.classifiers[self.best_model_name]
            pred = int(clf.predict(X)[0])
            prob = clf.predict_proba(X)[0]
            is_anomaly = pred == 1
            feat_label = "TF-IDF + Drain" if self.use_drain_features else "TF-IDF"
            return {
                "is_anomaly":    is_anomaly,
                "anomaly_score": float(prob[1] - prob[0]),
                "confidence":    float(prob[1] if is_anomaly else prob[0]),
                "reason":        f"Classified by {self.best_model_name} ({feat_label})",
                "model_used":    self.best_model_name,
                "error":         None,
            }
        except Exception as exc:
            logger.error(f"Prediction error: {exc}")
            return self._keyword_fallback(log_text)

    def parse_log(self, log_text: str):
        """Expose the underlying Drain parser for the API layer."""
        if self.structured_featurizer is None:
            return None
        return self.structured_featurizer.parser.parse_line(log_text)

    def get_log_templates(self, top_k: int = 25):
        """Top discovered Drain templates ordered by frequency."""
        if self.structured_featurizer is None:
            return []
        return self.structured_featurizer.parser.get_clusters(top_k=top_k)

    # ----- persistence -----------------------------------------------------

    def _save(self):
        path = os.path.join(MODELS_DIR, "supervised_classifier.pkl")
        with open(path, "wb") as fh:
            pickle.dump({
                "vectorizer":           self.vectorizer,
                "structured_featurizer": self.structured_featurizer,
                "use_drain_features":   self.use_drain_features,
                "classifiers":          self.classifiers,
                "best_model_name":      self.best_model_name,
                "cv_results":           self.cv_results,
                "test_metrics":         self.test_metrics,
                "feature_names":        self.feature_names,
            }, fh)
        logger.info(f"Saved classifier bundle -> {path}")

    def load_model(self) -> bool:
        path = os.path.join(MODELS_DIR, "supervised_classifier.pkl")
        try:
            with open(path, "rb") as fh:
                data = pickle.load(fh)
            self.vectorizer           = data["vectorizer"]
            self.classifiers          = data["classifiers"]
            self.best_model_name      = data["best_model_name"]
            self.cv_results           = data.get("cv_results", {})
            self.test_metrics         = data.get("test_metrics", {})
            self.feature_names        = data.get("feature_names", [])
            self.structured_featurizer = data.get("structured_featurizer")
            # Backward-compat: bundles saved before Drain integration won't
            # have a structured featurizer — keep the classifier in TF-IDF-only
            # mode so old pickles still load cleanly.
            self.use_drain_features   = data.get(
                "use_drain_features",
                self.structured_featurizer is not None,
            )
            self.is_trained           = True
            self._explainer           = None  # rebuild lazily on first explain() call
            logger.info(
                f"Loaded classifier (best = {self.best_model_name}, "
                f"drain={self.use_drain_features})"
            )
            return True
        except FileNotFoundError:
            logger.warning("No saved classifier found — run /api/train first.")
            return False
        except Exception as exc:
            logger.error(f"Load error: {exc}")
            return False

    # ----- keyword fallback (when model is not yet trained) ----------------

    _ERROR_PATTERNS = [
        re.compile(p, re.IGNORECASE) for p in [
            r"error", r"fatal", r"critical", r"exception",
            r"failed", r"timeout", r"crash", r"panic",
            r"outofmemory", r"stackoverflow", r"nullpointer",
            r"connection.*refused", r"permission denied",
            r"not.*found", r"disk.*full", r"unavailable",
        ]
    ]

    def _keyword_fallback(self, log_text: str) -> dict:
        count = sum(len(p.findall(log_text)) for p in self._ERROR_PATTERNS)
        is_anomaly = count > 0
        return {
            "is_anomaly":    is_anomaly,
            "anomaly_score": float(-0.5 * count) if is_anomaly else 0.0,
            "confidence":    min(0.9, 0.5 + 0.1 * count) if is_anomaly else 0.85,
            "reason":        f"Keyword fallback — {count} error pattern(s) matched",
            "model_used":    "keyword_fallback",
            "error":         None,
        }


# ---------------------------------------------------------------------------
# Backward-compatible alias used by pipeline.py and existing tests
# ---------------------------------------------------------------------------

class LogAnomalyDetector(SupervisedLogClassifier):
    """Drop-in alias kept for backward compatibility with existing code."""
    pass
