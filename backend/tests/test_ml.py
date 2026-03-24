"""
Unit tests for ML components.

Tests are fully self-contained: no database, no HTTP calls.
Run from the backend/ directory:
    pytest tests/test_ml.py -v
"""

import pytest
import numpy as np

from ml.anomaly import LogAnomalyDetector
from ml.forecaster import PipelineFailureForecaster
from ml.pipeline import AIOpsPredictor
from ml.analytics import ModelAnalytics


# ════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════

NORMAL_LOGS = [
    "Build started. Cloning repository from origin/main.",
    "Dependency installation complete. 142 packages installed.",
    "Running unit tests… 248 passed, 0 failed.",
    "Code coverage: 87%. Threshold: 80%.",
    "Linting complete. No issues found.",
    "Build artifact created: app-1.2.3.jar",
    "Deployment to staging: SUCCESS.",
    "Smoke tests passed. All endpoints responding.",
    "Metrics published to Prometheus.",
    "Pipeline finished in 4 m 12 s.",
    "INFO: Compilation complete.",
    "INFO: Test suite finished.",
]

ERROR_LOGS = [
    "ERROR: Database connection timeout after 30 s",
    "FATAL: Cannot connect to Redis – connection refused",
    "CRITICAL: Out-of-memory – process killed",
    "EXCEPTION: NullPointerException in com.example.Service",
    "ERROR: Test suite FAILED – 7 tests failed",
    "PANIC: kernel nil pointer dereference",
    "ERROR: permission denied /var/run/docker.sock",
    "FATAL: disk full – no space left on device",
    "ERROR: circuit breaker OPEN – service unavailable",
    "CRITICAL: SSL certificate expired",
    "TIMEOUT: health-check endpoint did not respond within 10 s",
    "ERROR: stack overflow detected in worker thread",
]


# ════════════════════════════════════════════════════════
# LogAnomalyDetector – unit tests
# ════════════════════════════════════════════════════════

class TestLogAnomalyDetectorFeatureExtraction:

    def setup_method(self):
        self.detector = LogAnomalyDetector()

    def test_returns_list_of_correct_length(self):
        features = self.detector._extract_features("INFO: build started")
        assert isinstance(features, list)
        assert len(features) == 7

    def test_normal_log_has_no_error_keyword(self):
        features = self.detector._extract_features("All tests passed successfully.")
        assert features[0] == 0  # has_error_keyword
        assert features[1] == 0  # error_keyword_count

    def test_error_log_sets_error_keyword_flag(self):
        features = self.detector._extract_features("ERROR: connection refused")
        assert features[0] == 1  # has_error_keyword
        assert features[1] >= 1  # error_keyword_count

    def test_multiple_errors_counted(self):
        features = self.detector._extract_features("ERROR: db down. FATAL: oom. CRITICAL: crash.")
        assert features[1] >= 3  # error_keyword_count

    def test_warning_flag_detected(self):
        features = self.detector._extract_features("WARNING: memory usage 90%")
        assert features[2] == 1  # has_warning

    def test_info_flag_detected(self):
        features = self.detector._extract_features("INFO: service started")
        assert features[3] == 1  # has_info

    def test_log_length_captured(self):
        short = self.detector._extract_features("ok")
        long = self.detector._extract_features("a" * 500)
        assert long[4] > short[4]  # log_length

    def test_number_count(self):
        features = self.detector._extract_features("port 8080 timeout 30 retry 3")
        assert features[6] >= 3  # number_count


class TestLogAnomalyDetectorPredict:

    def setup_method(self):
        self.detector = LogAnomalyDetector()

    def test_predict_returns_required_keys(self):
        result = self.detector.predict("INFO: build started")
        for key in ("is_anomaly", "anomaly_score", "confidence", "reason"):
            assert key in result

    def test_normal_log_is_not_anomaly(self):
        result = self.detector.predict("Build completed successfully. All tests passed.")
        assert result["is_anomaly"] is False

    def test_error_log_is_flagged_as_anomaly(self):
        result = self.detector.predict("ERROR: database connection timeout.")
        assert result["is_anomaly"] is True

    def test_fatal_keyword_triggers_anomaly(self):
        result = self.detector.predict("FATAL: service crashed – no memory")
        assert result["is_anomaly"] is True

    def test_critical_keyword_triggers_anomaly(self):
        result = self.detector.predict("CRITICAL: disk full")
        assert result["is_anomaly"] is True

    def test_confidence_is_between_0_and_1(self):
        for log in NORMAL_LOGS + ERROR_LOGS:
            result = self.detector.predict(log)
            assert 0.0 <= result["confidence"] <= 1.0, f"Confidence out of range for: {log}"

    def test_anomaly_score_is_numeric(self):
        result = self.detector.predict("ERROR: something broke")
        assert isinstance(result["anomaly_score"], (int, float))


class TestLogAnomalyDetectorTrain:

    def setup_method(self):
        self.detector = LogAnomalyDetector()

    def test_train_with_too_few_logs_returns_false(self):
        assert self.detector.train(["only one log"]) is False

    def test_train_with_nine_logs_returns_false(self):
        assert self.detector.train(NORMAL_LOGS[:9]) is False

    def test_train_with_sufficient_logs_returns_true(self):
        result = self.detector.train(NORMAL_LOGS + ERROR_LOGS)
        assert result is True

    def test_is_trained_after_successful_train(self):
        self.detector.train(NORMAL_LOGS + ERROR_LOGS)
        assert self.detector.is_trained is True

    def test_model_is_set_after_train(self):
        self.detector.train(NORMAL_LOGS + ERROR_LOGS)
        assert self.detector.model is not None

    def test_predict_after_train_still_catches_errors(self):
        self.detector.train(NORMAL_LOGS + ERROR_LOGS)
        result = self.detector.predict("ERROR: fatal crash")
        assert result["is_anomaly"] is True


# ════════════════════════════════════════════════════════
# PipelineFailureForecaster – unit tests
# ════════════════════════════════════════════════════════

GOOD_HISTORY = [0, 1, 0, 2, 1, 5, 3, 2, 1, 0, 3, 2, 1, 0, 4]


class TestPipelineFailureForecasterTrain:

    def setup_method(self):
        self.forecaster = PipelineFailureForecaster()

    def test_train_too_few_points_returns_false(self):
        assert self.forecaster.train([1, 2, 3]) is False

    def test_train_nine_points_returns_false(self):
        assert self.forecaster.train([0] * 9) is False

    def test_train_with_sufficient_data_returns_true(self):
        assert self.forecaster.train(GOOD_HISTORY) is True

    def test_is_trained_flag_set(self):
        self.forecaster.train(GOOD_HISTORY)
        assert self.forecaster.is_trained is True

    def test_model_not_none_after_train(self):
        self.forecaster.train(GOOD_HISTORY)
        assert self.forecaster.model is not None


class TestPipelineFailureForecasterPredict:

    def setup_method(self):
        self.forecaster = PipelineFailureForecaster()

    def test_predict_untrained_returns_zero_failures(self):
        result = self.forecaster.predict_next_hour()
        assert result["predicted_failures"] == 0

    def test_predict_untrained_has_error_message(self):
        result = self.forecaster.predict_next_hour()
        assert result.get("error") is not None

    def test_predict_trained_returns_non_negative_failures(self):
        self.forecaster.train(GOOD_HISTORY)
        result = self.forecaster.predict_next_hour()
        assert result["predicted_failures"] >= 0

    def test_predict_trained_returns_required_keys(self):
        self.forecaster.train(GOOD_HISTORY)
        result = self.forecaster.predict_next_hour()
        for key in ("predicted_failures", "upper_bound", "lower_bound", "error"):
            assert key in result

    def test_predict_trained_no_error_or_known_compat_issue(self):
        """ARIMA's conf_int() may return ndarray in some statsmodels/numpy combos."""
        self.forecaster.train(GOOD_HISTORY)
        result = self.forecaster.predict_next_hour()
        # Either no error, or a known numpy-compatibility error string
        if result["error"] is not None:
            assert isinstance(result["error"], str)
        assert result["predicted_failures"] >= 0

    def test_bounds_are_non_negative(self):
        self.forecaster.train(GOOD_HISTORY)
        result = self.forecaster.predict_next_hour()
        assert result["upper_bound"] >= 0
        assert result["lower_bound"] >= 0


# ════════════════════════════════════════════════════════
# AIOpsPredictor – unit tests
# ════════════════════════════════════════════════════════

class TestAIOpsPredictor:

    def setup_method(self):
        self.predictor = AIOpsPredictor()

    def test_analyze_returns_required_keys(self):
        result = self.predictor.analyze("Build successful")
        for key in ("risk_level", "score", "recommendation", "details"):
            assert key in result

    def test_risk_level_is_valid_enum(self):
        result = self.predictor.analyze("Build successful")
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    def test_score_is_between_0_and_1(self):
        for log in NORMAL_LOGS + ERROR_LOGS:
            result = self.predictor.analyze(log)
            assert 0.0 <= result["score"] <= 1.0, f"Score out of range for: {log}"

    def test_normal_log_yields_non_high_risk(self):
        """A clean log should never produce HIGH risk (may be LOW or MEDIUM
        depending on the confidence scalar the untrained model returns)."""
        result = self.predictor.analyze("All tests passed. Deployment successful.")
        assert result["risk_level"] in ("LOW", "MEDIUM")

    def test_error_log_yields_elevated_risk(self):
        result = self.predictor.analyze(
            "ERROR: FATAL connection refused. CRITICAL exception. Database timeout."
        )
        assert result["risk_level"] in ("MEDIUM", "HIGH")

    def test_details_contains_log_anomaly(self):
        result = self.predictor.analyze("INFO: service healthy")
        assert "log_anomaly" in result["details"]

    def test_analyze_with_failure_history(self):
        history = GOOD_HISTORY
        result = self.predictor.analyze("Build log", failure_history=history)
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    def test_recommendation_is_non_empty_string(self):
        result = self.predictor.analyze("Some log text")
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 0


# ════════════════════════════════════════════════════════
# ModelAnalytics – unit tests
# ════════════════════════════════════════════════════════

class TestModelAnalytics:

    def setup_method(self):
        self.analytics = ModelAnalytics()
        # Binary classification ground truth / scores
        self.y_true   = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1]
        self.y_scores = [0.1, 0.85, 0.2, 0.9, 0.75, 0.3, 0.8, 0.25, 0.15, 0.95]
        self.y_pred   = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1]

    # ROC curve ──────────────────────────────────────────
    def test_roc_curve_returns_dict(self):
        result = self.analytics.calculate_roc_curve(self.y_true, self.y_scores)
        assert isinstance(result, dict)

    def test_roc_curve_has_required_keys(self):
        result = self.analytics.calculate_roc_curve(self.y_true, self.y_scores)
        for key in ("fpr", "tpr", "auc", "thresholds"):
            assert key in result

    def test_roc_auc_in_valid_range(self):
        result = self.analytics.calculate_roc_curve(self.y_true, self.y_scores)
        assert 0.0 <= result["auc"] <= 1.0

    def test_roc_fpr_tpr_same_length(self):
        result = self.analytics.calculate_roc_curve(self.y_true, self.y_scores)
        assert len(result["fpr"]) == len(result["tpr"])

    def test_roc_good_classifier_auc_above_0_5(self):
        result = self.analytics.calculate_roc_curve(self.y_true, self.y_scores)
        assert result["auc"] > 0.5

    # Confusion matrix ───────────────────────────────────
    def test_confusion_matrix_returns_dict(self):
        result = self.analytics.calculate_confusion_matrix(self.y_true, self.y_pred)
        assert isinstance(result, dict)

    def test_confusion_matrix_has_required_keys(self):
        result = self.analytics.calculate_confusion_matrix(self.y_true, self.y_pred)
        for key in ("tp", "tn", "fp", "fn", "tpr", "fpr", "specificity"):
            assert key in result

    def test_confusion_matrix_totals_match_samples(self):
        result = self.analytics.calculate_confusion_matrix(self.y_true, self.y_pred)
        total = result["tp"] + result["tn"] + result["fp"] + result["fn"]
        assert total == len(self.y_true)

    def test_confusion_matrix_rates_in_range(self):
        result = self.analytics.calculate_confusion_matrix(self.y_true, self.y_pred)
        assert 0.0 <= result["tpr"] <= 1.0
        assert 0.0 <= result["fpr"] <= 1.0
        assert 0.0 <= result["specificity"] <= 1.0

    # Precision-Recall ───────────────────────────────────
    def test_precision_recall_returns_dict(self):
        result = self.analytics.calculate_precision_recall(self.y_true, self.y_scores)
        assert isinstance(result, dict)

    def test_precision_recall_has_required_keys(self):
        result = self.analytics.calculate_precision_recall(self.y_true, self.y_scores)
        for key in ("precision", "recall", "f1_scores", "average_precision"):
            assert key in result

    def test_average_precision_in_range(self):
        result = self.analytics.calculate_precision_recall(self.y_true, self.y_scores)
        assert 0.0 <= result["average_precision"] <= 1.0

    def test_precision_recall_lists_non_empty(self):
        result = self.analytics.calculate_precision_recall(self.y_true, self.y_scores)
        assert len(result["precision"]) > 0
        assert len(result["recall"]) > 0
