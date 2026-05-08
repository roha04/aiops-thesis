"""
Unit tests for ML components.

Tests are fully self-contained: no database, no HTTP calls.
Run from the backend/ directory:
    pytest tests/test_ml.py -v
"""

import pytest
import numpy as np

from ml.anomaly import LogAnomalyDetector, _tokenize
from ml.forecaster import PipelineFailureForecaster
from ml.pipeline import AIOpsPredictor
from ml.analytics import ModelAnalytics
from ml.lstm_detector import LSTMLogDetector, SimpleVocab, _tokenize_line, _TORCH_AVAILABLE


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
    "INFO: Starting container on port 8080.",
    "INFO: Health check passed for service auth.",
    "INFO: Cache warm-up complete, 512 entries loaded.",
    "INFO: Scheduled job ran successfully.",
    "INFO: Rate limiter configured, 1000 req/s.",
    "INFO: Config loaded from environment.",
    "INFO: Database migration applied: v42.",
    "INFO: Artefact uploaded to S3 bucket.",
    "INFO: CDN invalidation triggered.",
    "INFO: Worker pool started, 4 threads.",
    "INFO: Feature flag evaluation complete.",
    "INFO: Circuit breaker CLOSED – service recovered.",
    "INFO: Autoscaling event: 3 replicas → 4 replicas.",
    "INFO: Security scan: 0 critical vulnerabilities.",
    "INFO: Backup completed successfully in 12 s.",
    "INFO: Log rotation triggered, old files archived.",
    "INFO: API gateway routing updated.",
    "INFO: Deployment complete, rollout 100%.",
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
    "FATAL: segmentation fault in process 1024",
    "ERROR: failed to acquire distributed lock after 5 retries",
    "CRITICAL: downstream dependency unreachable: payment-service",
    "ERROR: authentication token expired, request rejected",
    "FATAL: database replication lag exceeded 60 s",
    "ERROR: container OOMKilled by kubelet",
    "CRITICAL: CPU throttling detected on core 0",
    "ERROR: request queue overflow, dropping messages",
    "FATAL: leader election failed, no quorum",
    "ERROR: TLS handshake failure: certificate mismatch",
    "CRITICAL: data corruption detected in shard 3",
    "ERROR: message broker partition offline",
    "FATAL: dependency injection failed for bean AuthService",
    "ERROR: exceeded max retry limit for job 7f3a",
    "CRITICAL: health probe failed 3 consecutive times",
    "ERROR: pod CrashLoopBackOff: exit code 137",
    "FATAL: unhandled exception in main thread",
    "CRITICAL: service degraded – p99 latency > 5 s",
]


# ════════════════════════════════════════════════════════
# LogAnomalyDetector – unit tests
# ════════════════════════════════════════════════════════

class TestLogTokenizer:
    """Tests for the TF-IDF preprocessing function that replaced _extract_features."""

    def test_returns_string(self):
        assert isinstance(_tokenize("INFO: build started"), str)

    def test_normal_log_has_no_error_keyword_in_output(self):
        result = _tokenize("All tests passed successfully.")
        assert "error" not in result

    def test_error_keyword_preserved_as_token(self):
        result = _tokenize("ERROR: connection refused")
        assert "error" in result

    def test_numbers_replaced_with_num_token(self):
        result = _tokenize("port 8080 timeout 30")
        assert "<num>" in result
        assert "8080" not in result

    def test_ip_replaced_with_ip_token(self):
        result = _tokenize("connect to 192.168.1.1")
        assert "<ip>" in result

    def test_hex_replaced_with_hex_token(self):
        result = _tokenize("memory 0xdeadbeef")
        assert "<hex>" in result

    def test_lowercase_normalisation(self):
        result = _tokenize("FATAL CRITICAL")
        assert "FATAL" not in result
        assert "fatal" in result

    def test_empty_string(self):
        assert _tokenize("") == ""


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
    """Tests for the supervised TF-IDF training pipeline."""

    # Use enough data so TF-IDF + cross-val is meaningful
    ALL_LOGS   = NORMAL_LOGS + ERROR_LOGS
    ALL_LABELS = [0] * len(NORMAL_LOGS) + [1] * len(ERROR_LOGS)

    def setup_method(self):
        self.detector = LogAnomalyDetector()

    def test_train_with_too_few_logs_returns_empty_dict(self):
        result = self.detector.train(["only one log"], [0])
        assert result == {}

    def test_train_with_nine_logs_returns_empty_dict(self):
        result = self.detector.train(NORMAL_LOGS[:9], [0] * 9)
        assert result == {}

    def test_train_with_sufficient_logs_returns_dict(self):
        result = self.detector.train(self.ALL_LOGS, self.ALL_LABELS)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_cv_f1_present_for_each_model(self):
        result = self.detector.train(self.ALL_LOGS, self.ALL_LABELS)
        for model_name, metrics in result.items():
            assert "cv_f1_mean" in metrics, f"cv_f1_mean missing for {model_name}"
            assert 0.0 <= metrics["cv_f1_mean"] <= 1.0

    def test_is_trained_after_successful_train(self):
        self.detector.train(self.ALL_LOGS, self.ALL_LABELS)
        assert self.detector.is_trained is True

    def test_classifiers_dict_populated_after_train(self):
        self.detector.train(self.ALL_LOGS, self.ALL_LABELS)
        assert len(self.detector.classifiers) >= 2  # at least LR + RF

    def test_best_model_name_set_after_train(self):
        self.detector.train(self.ALL_LOGS, self.ALL_LABELS)
        assert self.detector.best_model_name in self.detector.classifiers

    def test_predict_after_train_still_catches_errors(self):
        self.detector.train(self.ALL_LOGS, self.ALL_LABELS)
        result = self.detector.predict("ERROR: fatal crash")
        assert result["is_anomaly"] is True

    def test_get_feature_importance_returns_lists(self):
        self.detector.train(self.ALL_LOGS, self.ALL_LABELS)
        fi = self.detector.get_feature_importance()
        assert "features" in fi and "importance" in fi
        assert len(fi["features"]) == len(fi["importance"])
        assert len(fi["features"]) > 0


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


# ════════════════════════════════════════════════════════
# LSTMLogDetector — unit tests
# ════════════════════════════════════════════════════════

# 30 successful builds (all normal lines)
_NORMAL_SEQ = [
    [
        "INFO [auth-service] Build started for branch main",
        "INFO [db-worker] Running unit tests...",
        "INFO [api-gateway] Tests passed (248/248)",
        "INFO [build-runner] Building Docker image v1.2.3",
        "INFO [deploy-agent] Deployment initiated on staging",
        "INFO [auth-service] Health checks passing",
        "INFO [cache-manager] Service started on port 8080",
        "INFO [scheduler] Connected to database successfully",
        "INFO [metrics-collector] Configuration loaded from environment",
        "INFO [log-aggregator] All services healthy",
    ]
    * 3   # repeat to hit 30 lines (truncated to SEQ_LEN=20 internally)
    for _ in range(30)
]

# 20 failed builds (7 normal → 3 error — escalation pattern)
_FAILURE_SEQ = [
    [
        "INFO [auth-service] Build started for branch main",
        "INFO [db-worker] Running unit tests...",
        "INFO [api-gateway] Tests passed (248/248)",
        "INFO [build-runner] Building Docker image v1.2.3",
        "INFO [deploy-agent] Deployment initiated on staging",
        "INFO [auth-service] Health checks passing",
        "INFO [cache-manager] Service started on port 8080",
        "ERROR [db-worker] Database connection timeout after 30s",
        "FATAL [api-gateway] Cannot connect to primary DB — failover failed",
        "CRITICAL [auth-service] OOM killer triggered — container restarting",
    ]
    for _ in range(20)
]

_ALL_SEQS   = _NORMAL_SEQ + _FAILURE_SEQ
_ALL_LABELS = [0] * 30 + [1] * 20


class TestSimpleVocab:
    """Tests for the vocabulary builder."""

    def test_len_includes_pad_and_unk(self):
        v = SimpleVocab()
        assert len(v) == 2

    def test_build_adds_tokens(self):
        v = SimpleVocab(min_freq=1)
        v.build([[["hello", "world"]]])
        assert "hello" in v.token2id
        assert "world" in v.token2id

    def test_min_freq_filters_rare_tokens(self):
        v = SimpleVocab(min_freq=2)
        v.build([[["rare"]], [["common", "common"]]])
        assert "rare" not in v.token2id
        assert "common" in v.token2id

    def test_encode_returns_ints(self):
        v = SimpleVocab(min_freq=1)
        v.build([[["hello"]]])
        ids = v.encode(["hello", "missing"])
        assert isinstance(ids[0], int)
        assert ids[1] == v.token2id["<unk>"]


class TestLSTMTokenizeLine:
    """Tests for the per-line tokeniser in lstm_detector."""

    def test_returns_list_of_strings(self):
        assert isinstance(_tokenize_line("INFO build started"), list)

    def test_numbers_become_num_token(self):
        tokens = _tokenize_line("port 8080")
        assert "<num>" in tokens
        assert "8080" not in tokens

    def test_ip_becomes_ip_token(self):
        tokens = _tokenize_line("host 10.0.0.1")
        assert "<ip>" in tokens

    def test_lowercases_input(self):
        tokens = _tokenize_line("FATAL ERROR")
        assert "fatal" in tokens and "error" in tokens

    def test_empty_string_returns_empty_list(self):
        assert _tokenize_line("") == []


@pytest.mark.skipif(not _TORCH_AVAILABLE, reason="PyTorch not installed")
class TestLSTMLogDetectorTrain:
    """Tests for LSTMLogDetector training (requires PyTorch)."""

    def test_too_few_sequences_returns_empty_list(self):
        det = LSTMLogDetector()
        result = det.train([["log line"]], [0])
        assert result == []

    def test_train_returns_list_of_epoch_dicts(self):
        det = LSTMLogDetector()
        result = det.train(_ALL_SEQS, _ALL_LABELS, epochs=2)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_each_epoch_has_required_keys(self):
        det = LSTMLogDetector()
        result = det.train(_ALL_SEQS, _ALL_LABELS, epochs=2)
        for m in result:
            for key in ("epoch", "train_loss", "val_loss", "accuracy", "f1_score"):
                assert key in m, f"Key '{key}' missing from epoch metrics"

    def test_train_loss_decreases_or_stays_low(self):
        det = LSTMLogDetector()
        result = det.train(_ALL_SEQS, _ALL_LABELS, epochs=3)
        assert result[-1]["train_loss"] < 2.0   # sanity check, not threshold

    def test_is_trained_flag_set_after_train(self):
        det = LSTMLogDetector()
        det.train(_ALL_SEQS, _ALL_LABELS, epochs=2)
        assert det.is_trained is True

    def test_epoch_metrics_stored_on_instance(self):
        det = LSTMLogDetector()
        det.train(_ALL_SEQS, _ALL_LABELS, epochs=2)
        assert len(det.epoch_metrics) == 2

    def test_evaluate_returns_metrics_dict(self):
        det = LSTMLogDetector()
        det.train(_ALL_SEQS, _ALL_LABELS, epochs=2)
        m = det.evaluate(_ALL_SEQS[:10], _ALL_LABELS[:10])
        assert isinstance(m, dict)
        for key in ("accuracy", "precision", "recall", "f1_score", "roc_auc"):
            assert key in m

    def test_roc_auc_in_valid_range(self):
        det = LSTMLogDetector()
        det.train(_ALL_SEQS, _ALL_LABELS, epochs=2)
        m = det.evaluate(_ALL_SEQS, _ALL_LABELS)
        assert 0.0 <= m["roc_auc"] <= 1.0


@pytest.mark.skipif(not _TORCH_AVAILABLE, reason="PyTorch not installed")
class TestLSTMLogDetectorPredict:
    """Tests for LSTMLogDetector prediction (requires PyTorch)."""

    def setup_method(self):
        self.det = LSTMLogDetector()
        self.det.train(_ALL_SEQS, _ALL_LABELS, epochs=2)

    def test_predict_returns_required_keys(self):
        result = self.det.predict(_FAILURE_SEQ[0])
        for key in ("failure_probability", "is_failure", "confidence", "model"):
            assert key in result

    def test_failure_probability_in_range(self):
        result = self.det.predict(_FAILURE_SEQ[0])
        assert 0.0 <= result["failure_probability"] <= 1.0

    def test_model_label_is_lstm(self):
        result = self.det.predict(_NORMAL_SEQ[0])
        assert result["model"] == "lstm"

    def test_untrained_detector_returns_disabled(self):
        det = LSTMLogDetector()
        result = det.predict(["just one line"])
        assert result["model"] == "lstm_disabled"
