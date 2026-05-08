"""
Log Anomaly Detection — Supervised TF-IDF + Multi-Classifier Pipeline

Models    : Logistic Regression, Random Forest, XGBoost
Evaluation: 5-fold stratified cross-validation
Inference : best model (by CV F1) used at prediction time
"""

import re
import os
import pickle
import logging

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
)

try:
    from xgboost import XGBClassifier
    _XGBOOST = True
except ImportError:
    _XGBOOST = False

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

    Trains Logistic Regression, Random Forest, and XGBoost on TF-IDF
    features with 5-fold stratified cross-validation, then retains the
    best model for real-time inference.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            preprocessor=_tokenize,
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
        )
        self.classifiers: dict = {}
        self.best_model_name: str = "Random Forest"
        self.cv_results: dict = {}
        self.test_metrics: dict = {}
        self.feature_names: list = []
        self.is_trained: bool = False

    # ----- training --------------------------------------------------------

    def train(self, logs: list, labels: list) -> dict:
        """
        Fit TF-IDF + all classifiers with 5-fold CV, then retrain on full set.
        Returns per-model CV metrics dict.
        """
        if len(logs) < 50:
            logger.warning("Need at least 50 samples; skipping training.")
            return {}

        logger.info(f"Fitting TF-IDF on {len(logs)} samples ...")
        X = self.vectorizer.fit_transform([_tokenize(l) for l in logs])
        y = np.array(labels)
        self.feature_names = self.vectorizer.get_feature_names_out().tolist()

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
        self._save()
        return cv_results

    # ----- evaluation ------------------------------------------------------

    def evaluate_on_test(self, logs: list, labels: list) -> dict:
        """Compute held-out test metrics for every trained classifier."""
        if not self.is_trained:
            return {}
        X = self.vectorizer.transform([_tokenize(l) for l in logs])
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

    # ----- predict (uses best model at inference time) ---------------------

    def predict(self, log_text: str) -> dict:
        """Single-sample prediction using the best trained classifier."""
        if not self.is_trained:
            return self._keyword_fallback(log_text)
        try:
            X = self.vectorizer.transform([_tokenize(log_text)])
            clf = self.classifiers[self.best_model_name]
            pred = int(clf.predict(X)[0])
            prob = clf.predict_proba(X)[0]
            is_anomaly = pred == 1
            return {
                "is_anomaly":    is_anomaly,
                "anomaly_score": float(prob[1] - prob[0]),
                "confidence":    float(prob[1] if is_anomaly else prob[0]),
                "reason":        f"Classified by {self.best_model_name} (TF-IDF)",
                "model_used":    self.best_model_name,
                "error":         None,
            }
        except Exception as exc:
            logger.error(f"Prediction error: {exc}")
            return self._keyword_fallback(log_text)

    # ----- persistence -----------------------------------------------------

    def _save(self):
        path = os.path.join(MODELS_DIR, "supervised_classifier.pkl")
        with open(path, "wb") as fh:
            pickle.dump({
                "vectorizer":      self.vectorizer,
                "classifiers":     self.classifiers,
                "best_model_name": self.best_model_name,
                "cv_results":      self.cv_results,
                "test_metrics":    self.test_metrics,
                "feature_names":   self.feature_names,
            }, fh)
        logger.info(f"Saved classifier bundle -> {path}")

    def load_model(self) -> bool:
        path = os.path.join(MODELS_DIR, "supervised_classifier.pkl")
        try:
            with open(path, "rb") as fh:
                data = pickle.load(fh)
            self.vectorizer      = data["vectorizer"]
            self.classifiers     = data["classifiers"]
            self.best_model_name = data["best_model_name"]
            self.cv_results      = data.get("cv_results", {})
            self.test_metrics    = data.get("test_metrics", {})
            self.feature_names   = data.get("feature_names", [])
            self.is_trained      = True
            logger.info(f"Loaded classifier (best = {self.best_model_name})")
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
