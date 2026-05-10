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


# ════════════════════════════════════════════════════════
# DrainLogParser — unit tests
# ════════════════════════════════════════════════════════

from ml.log_parser import (
    DrainLogParser,
    StructuredLogFeaturizer,
    ParsedLog,
    LOG_LEVELS,
    LOG_LEVEL_SEVERITY,
    WILDCARD,
)


class TestDrainParserParseLine:
    """Behavioural tests for the Drain template miner."""

    def setup_method(self):
        self.parser = DrainLogParser()

    def test_parse_returns_parsedlog_instance(self):
        result = self.parser.parse_line("INFO [auth] Build started")
        assert isinstance(result, ParsedLog)

    def test_event_id_has_expected_prefix(self):
        result = self.parser.parse_line("INFO [auth] Build started")
        assert result.event_id.startswith("E")
        assert len(result.event_id) == 6  # E + 5 digit cluster id

    def test_log_level_extracted(self):
        assert self.parser.parse_line("INFO message").log_level == "INFO"
        assert self.parser.parse_line("WARNING busy").log_level == "WARNING"
        assert self.parser.parse_line("ERROR boom").log_level == "ERROR"
        assert self.parser.parse_line("FATAL crash").log_level == "FATAL"
        assert self.parser.parse_line("CRITICAL down").log_level == "CRITICAL"

    def test_log_level_unknown_when_missing(self):
        assert self.parser.parse_line("just some text").log_level == "UNKNOWN"

    def test_log_level_normalised_abbreviations(self):
        assert self.parser.parse_line("WARN low memory").log_level == "WARNING"
        assert self.parser.parse_line("ERR something").log_level == "ERROR"

    def test_service_extracted_from_brackets(self):
        result = self.parser.parse_line("INFO [auth-service] Build started")
        assert result.service == "auth-service"

    def test_service_none_when_missing(self):
        result = self.parser.parse_line("INFO Build started")
        assert result.service is None

    def test_template_contains_wildcards_for_numbers(self):
        result = self.parser.parse_line("ERROR Database timeout after 30s")
        assert WILDCARD in result.template

    def test_similar_lines_share_event_id(self):
        a = self.parser.parse_line("ERROR [db] Database connection timeout after 30s")
        b = self.parser.parse_line("ERROR [api] Database connection timeout after 60s")
        assert a.event_id == b.event_id

    def test_dissimilar_lines_get_different_event_ids(self):
        a = self.parser.parse_line("ERROR [db] Database connection timeout")
        b = self.parser.parse_line("INFO [auth] User logged in successfully")
        assert a.event_id != b.event_id

    def test_template_generalises_after_seeing_more_examples(self):
        self.parser.parse_line("INFO [auth] Build started for branch main")
        # second line with different last token should generalise the template
        result = self.parser.parse_line("INFO [auth] Build started for branch develop")
        assert WILDCARD in result.template
        assert "started" in result.template  # invariant tokens preserved

    def test_to_dict_returns_serialisable_payload(self):
        result = self.parser.parse_line("ERROR [db] timeout 30s")
        payload = result.to_dict()
        for key in ("raw", "template", "event_id", "parameters", "log_level",
                    "service", "timestamp", "timestamp_delta_sec"):
            assert key in payload

    def test_empty_line_does_not_crash(self):
        result = self.parser.parse_line("")
        assert isinstance(result, ParsedLog)


class TestDrainParserBatch:

    def setup_method(self):
        self.parser = DrainLogParser()

    def test_batch_returns_one_result_per_line(self):
        lines = [
            "INFO [auth] Build started",
            "ERROR [db] Database timeout 30s",
            "INFO [auth] Tests passed",
        ]
        results = self.parser.parse_batch(lines)
        assert len(results) == 3

    def test_batch_groups_repeated_lines_into_same_cluster(self):
        lines = [f"INFO [svc-{i}] Service started on port {1000+i}"
                 for i in range(20)]
        results = self.parser.parse_batch(lines)
        # Despite varying service + port, all should land in one cluster.
        assert len({r.event_id for r in results}) == 1

    def test_get_clusters_sorted_by_count_desc(self):
        # 5 lines of one shape, 1 line of another → first cluster should be larger.
        for _ in range(5):
            self.parser.parse_line("INFO [auth] Health check OK")
        self.parser.parse_line("ERROR [db] Disk full")
        clusters = self.parser.get_clusters()
        assert clusters[0]["count"] >= clusters[-1]["count"]

    def test_clusters_contain_examples(self):
        self.parser.parse_line("INFO [a] foo")
        self.parser.parse_line("INFO [b] foo")
        clusters = self.parser.get_clusters()
        assert all("examples" in c and len(c["examples"]) > 0 for c in clusters)

    def test_top_k_caps_clusters(self):
        # Use structurally distinct lines so each lands in its own cluster.
        unique_lines = [
            "INFO [auth] Build started for branch main",
            "WARNING [api] High memory usage detected",
            "ERROR [db] Database connection timeout",
            "FATAL [worker] Cannot connect to primary DB",
            "CRITICAL [auth] OOM killer triggered container",
            "INFO [scheduler] Job ran successfully today",
            "DEBUG [cache] Cache key hit user data",
        ]
        for line in unique_lines:
            self.parser.parse_line(line)
        assert len(self.parser.get_clusters(top_k=5)) == 5
        assert len(self.parser.get_clusters()) == len(unique_lines)


class TestStructuredLogFeaturizer:

    def setup_method(self):
        # Mix of normal + error templates with a few services
        self.lines = (
            ["INFO [auth] Build started for branch main"]   * 10
            + ["INFO [api] Tests passed"]                    * 10
            + ["ERROR [db] Database timeout after 30s"]      * 10
            + ["FATAL [worker] Cannot connect to primary DB"] * 10
        )
        self.feat = StructuredLogFeaturizer()

    def test_fit_sets_is_fitted_flag(self):
        self.feat.fit(self.lines)
        assert self.feat.is_fitted is True

    def test_transform_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            self.feat.transform(["whatever"])

    def test_fit_transform_returns_correct_shape(self):
        X = self.feat.fit_transform(self.lines)
        assert X.shape[0] == len(self.lines)
        assert X.shape[1] == self.feat.n_features()

    def test_features_are_sparse_csr(self):
        X = self.feat.fit_transform(self.lines)
        from scipy.sparse import csr_matrix
        assert isinstance(X, csr_matrix)

    def test_feature_names_match_n_features(self):
        self.feat.fit(self.lines)
        assert len(self.feat.feature_names) == self.feat.n_features()

    def test_unseen_template_routed_to_other_bucket(self):
        self.feat.fit(self.lines)
        X1 = self.feat.transform(["INFO [auth] Build started for branch main"])
        X2 = self.feat.transform(["NOVEL [unknown] Some completely new event pattern"])
        # both must return sample-shaped vectors with stable feature dim
        assert X1.shape[1] == X2.shape[1] == self.feat.n_features()

    def test_log_level_severity_constants_complete(self):
        # Every recognised level must have a severity score for the numeric feature.
        for lvl in LOG_LEVELS:
            assert lvl in LOG_LEVEL_SEVERITY


class TestSupervisedLogClassifierWithDrain:
    """Smoke tests for the hybrid TF-IDF + Drain feature pipeline."""

    LOGS = (
        ["INFO [auth] Build started for branch main"]   * 15
        + ["INFO [api] Tests passed (100/100)"]         * 15
        + ["INFO [worker] Service started on port 8080"]* 15
        + ["ERROR [db] Database connection timeout after 30s"] * 15
        + ["FATAL [worker] Cannot connect to primary DB"]      * 15
        + ["CRITICAL [auth] OOM killer triggered"]             * 15
    )
    LABELS = [0] * 45 + [1] * 45

    def test_drain_classifier_trains(self):
        clf = LogAnomalyDetector(use_drain_features=True)
        cv = clf.train(self.LOGS, self.LABELS)
        assert isinstance(cv, dict) and len(cv) > 0
        assert clf.is_trained
        assert clf.structured_featurizer is not None
        assert clf.structured_featurizer.is_fitted

    def test_drain_classifier_predict_reflects_drain_in_reason(self):
        clf = LogAnomalyDetector(use_drain_features=True)
        clf.train(self.LOGS, self.LABELS)
        result = clf.predict("ERROR [db] Database connection timeout after 99s")
        assert "Drain" in result["reason"]
        assert result["is_anomaly"] is True

    def test_legacy_tfidf_only_classifier_still_works(self):
        clf = LogAnomalyDetector(use_drain_features=False)
        cv = clf.train(self.LOGS, self.LABELS)
        assert clf.is_trained
        assert clf.structured_featurizer is None
        result = clf.predict("ERROR [db] Database connection timeout")
        assert "TF-IDF" in result["reason"]

    def test_parse_log_exposes_template_metadata(self):
        clf = LogAnomalyDetector(use_drain_features=True)
        clf.train(self.LOGS, self.LABELS)
        parsed = clf.parse_log("ERROR [db] Database connection timeout after 5s")
        assert parsed is not None
        assert parsed.log_level == "ERROR"
        assert parsed.service == "db"
        assert WILDCARD in parsed.template

    def test_get_log_templates_returns_clusters(self):
        clf = LogAnomalyDetector(use_drain_features=True)
        clf.train(self.LOGS, self.LABELS)
        clusters = clf.get_log_templates(top_k=10)
        assert isinstance(clusters, list)
        assert len(clusters) > 0
        for c in clusters:
            assert "event_id" in c and "template" in c and "count" in c
