"""
Integration tests for the FastAPI backend.

Uses a SQLite database (no PostgreSQL required) injected via FastAPI
dependency overrides. All HTTP calls go through TestClient (no real network).

Run from the backend/ directory:
    pytest tests/test_api.py -v
"""

import pytest
from datetime import datetime

# conftest.py provides: client, db_session fixtures
from db.models import (
    Prediction, Alert, ModelMetrics, TrainingData,
    TrainingHistory,
)


# ════════════════════════════════════════════════════════
# /health
# ════════════════════════════════════════════════════════

class TestHealthEndpoint:

    def test_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_is_ok(self, client):
        data = response = client.get("/health").json()
        assert data["status"] == "ok"

    def test_service_name_present(self, client):
        data = client.get("/health").json()
        assert "service" in data
        assert "AIOps" in data["service"]

    def test_version_present(self, client):
        data = client.get("/health").json()
        assert "version" in data


# ════════════════════════════════════════════════════════
# POST /api/predict
# ════════════════════════════════════════════════════════

class TestPredictEndpoint:

    def test_basic_predict_returns_200(self, client):
        response = client.post(
            "/api/predict",
            params={"pipeline_id": "pipe-001", "logs": "Build successful. Tests passed."},
        )
        assert response.status_code == 200

    def test_response_has_required_keys(self, client):
        response = client.post(
            "/api/predict",
            params={"pipeline_id": "pipe-001", "logs": "INFO: all good"},
        )
        data = response.json()
        for key in ("pipeline_id", "prediction_id", "timestamp", "prediction"):
            assert key in data

    def test_pipeline_id_echoed_back(self, client):
        response = client.post(
            "/api/predict",
            params={"pipeline_id": "my-unique-pipeline", "logs": "Healthy build"},
        )
        assert response.json()["pipeline_id"] == "my-unique-pipeline"

    def test_prediction_contains_risk_level(self, client):
        response = client.post(
            "/api/predict",
            params={"pipeline_id": "pipe-riskcheck", "logs": "Build success"},
        )
        prediction = response.json()["prediction"]
        assert prediction["risk_level"] in ("LOW", "MEDIUM", "HIGH")

    def test_error_log_returns_elevated_risk(self, client):
        response = client.post(
            "/api/predict",
            params={
                "pipeline_id": "pipe-error",
                "logs": "ERROR: FATAL database timeout. CRITICAL service unavailable.",
            },
        )
        assert response.status_code == 200
        prediction = response.json()["prediction"]
        assert prediction["risk_level"] in ("MEDIUM", "HIGH")

    def test_predict_without_logs_param_uses_default(self, client):
        response = client.post(
            "/api/predict",
            params={"pipeline_id": "pipe-nolog"},
        )
        assert response.status_code == 200

    def test_prediction_saved_to_db(self, client, db_session):
        count_before = db_session.query(Prediction).count()
        client.post(
            "/api/predict",
            params={"pipeline_id": "pipe-dbcheck", "logs": "Build success"},
        )
        count_after = db_session.query(Prediction).count()
        assert count_after == count_before + 1


# ════════════════════════════════════════════════════════
# GET /api/predictions
# ════════════════════════════════════════════════════════

class TestPredictionsHistoryEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/predictions").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/predictions").json(), list)

    def test_limit_parameter_respected(self, client, db_session):
        for i in range(6):
            pred = Prediction(
                pipeline_id=f"pipe-limit-{i}",
                log_snippet="test",
                is_anomaly=False,
                anomaly_score=0.1,
                anomaly_confidence=0.9,
                predicted_failures=0,
                risk_level="LOW",
                risk_score=0.1,
                recommendation="All clear",
            )
            db_session.add(pred)
        db_session.flush()

        response = client.get("/api/predictions?limit=3")
        assert len(response.json()) <= 3

    def test_each_item_has_required_fields(self, client, db_session):
        db_session.add(
            Prediction(
                pipeline_id="pipe-field-check",
                log_snippet="log",
                is_anomaly=True,
                anomaly_score=0.8,
                anomaly_confidence=0.9,
                predicted_failures=2,
                risk_level="HIGH",
                risk_score=0.85,
                recommendation="Check pipeline",
            )
        )
        db_session.flush()

        items = client.get("/api/predictions?limit=50").json()
        assert len(items) > 0
        item = items[0]
        for field in ("id", "pipeline_id", "risk_level", "anomaly_score", "created_at"):
            assert field in item


# ════════════════════════════════════════════════════════
# GET /api/alerts
# ════════════════════════════════════════════════════════

class TestAlertsEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/alerts").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/alerts").json(), list)

    def test_alert_structure(self, client, db_session):
        db_session.add(
            Alert(
                prediction_id=1,
                pipeline_id="pipe-alert-struct",
                alert_type="ANOMALY",
                severity="WARNING",
                message="Test alert message",
                is_resolved=False,
            )
        )
        db_session.flush()

        alerts = client.get("/api/alerts").json()
        assert len(alerts) > 0
        alert = alerts[0]
        assert "_id" in alert
        assert "_source" in alert
        src = alert["_source"]
        for field in ("timestamp", "pipeline_id", "severity", "message", "is_resolved"):
            assert field in src

    def test_severity_values_are_valid(self, client, db_session):
        for sev in ("INFO", "WARNING", "CRITICAL"):
            db_session.add(
                Alert(
                    prediction_id=1,
                    pipeline_id="pipe-sev-test",
                    alert_type="ANOMALY",
                    severity=sev,
                    message=f"{sev} message",
                    is_resolved=False,
                )
            )
        db_session.flush()

        alerts = client.get("/api/alerts").json()
        valid = {"INFO", "WARNING", "CRITICAL"}
        for a in alerts:
            assert a["_source"]["severity"] in valid

    def test_limit_parameter_respected(self, client, db_session):
        for i in range(5):
            db_session.add(
                Alert(
                    prediction_id=1,
                    pipeline_id=f"pipe-lim-{i}",
                    alert_type="ANOMALY",
                    severity="INFO",
                    message="msg",
                    is_resolved=False,
                )
            )
        db_session.flush()

        alerts = client.get("/api/alerts?limit=2").json()
        assert len(alerts) <= 2


# ════════════════════════════════════════════════════════
# GET /api/metrics
# ════════════════════════════════════════════════════════

class TestMetricsEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/metrics").status_code == 200

    def test_returns_required_keys(self, client):
        data = client.get("/api/metrics").json()
        for key in ("accuracy", "precision", "recall", "f1_score"):
            assert key in data

    def test_default_values_without_db_data(self, client):
        data = client.get("/api/metrics").json()
        # Defaults: accuracy >= 0
        assert data["accuracy"] >= 0.0

    def test_returns_stored_metrics_when_present(self, client, db_session):
        db_session.add(
            ModelMetrics(
                model_version="v-test",
                accuracy=0.93,
                precision=0.91,
                recall=0.90,
                f1_score=0.905,
                test_samples=200,
                true_positives=90,
                true_negatives=96,
                false_positives=9,
                false_negatives=5,
                training_samples=800,
            )
        )
        db_session.flush()

        data = client.get("/api/metrics").json()
        assert abs(data["accuracy"] - 0.93) < 0.001


# ════════════════════════════════════════════════════════
# GET /api/dashboard
# ════════════════════════════════════════════════════════

class TestDashboardEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/dashboard").status_code == 200

    def test_has_total_alerts(self, client):
        data = client.get("/api/dashboard").json()
        assert "total_alerts" in data

    def test_has_critical_issues(self, client):
        data = client.get("/api/dashboard").json()
        assert "critical_issues" in data

    def test_total_alerts_is_integer(self, client):
        data = client.get("/api/dashboard").json()
        assert isinstance(data["total_alerts"], int)

    def test_critical_issues_is_integer(self, client):
        data = client.get("/api/dashboard").json()
        assert isinstance(data["critical_issues"], int)


# ════════════════════════════════════════════════════════
# GET /api/analytics/summary
# ════════════════════════════════════════════════════════

class TestAnalyticsSummaryEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/analytics/summary").status_code == 200

    def test_has_summary_key(self, client):
        data = client.get("/api/analytics/summary").json()
        assert "summary" in data

    def test_summary_has_required_fields(self, client):
        summary = client.get("/api/analytics/summary").json()["summary"]
        for field in (
            "total_predictions", "total_anomalies",
            "anomaly_rate", "total_alerts",
            "model_accuracy", "model_f1",
        ):
            assert field in summary

    def test_anomaly_rate_is_numeric(self, client):
        summary = client.get("/api/analytics/summary").json()["summary"]
        assert isinstance(summary["anomaly_rate"], (int, float))

    def test_model_accuracy_in_range(self, client):
        summary = client.get("/api/analytics/summary").json()["summary"]
        assert 0.0 <= summary["model_accuracy"] <= 1.0


# ════════════════════════════════════════════════════════
# GET /api/analytics/roc-curve
# ════════════════════════════════════════════════════════

class TestROCCurveEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/analytics/roc-curve").status_code == 200

    def test_has_roc_curve_key(self, client):
        data = client.get("/api/analytics/roc-curve").json()
        assert "roc_curve" in data

    def test_roc_curve_has_fpr_tpr_auc(self, client):
        roc = client.get("/api/analytics/roc-curve").json()["roc_curve"]
        for field in ("fpr", "tpr", "auc"):
            assert field in roc

    def test_fpr_tpr_are_lists(self, client):
        roc = client.get("/api/analytics/roc-curve").json()["roc_curve"]
        assert isinstance(roc["fpr"], list)
        assert isinstance(roc["tpr"], list)

    def test_auc_is_numeric(self, client):
        roc = client.get("/api/analytics/roc-curve").json()["roc_curve"]
        assert isinstance(roc["auc"], (int, float))


# ════════════════════════════════════════════════════════
# GET /api/analytics/training-history
# ════════════════════════════════════════════════════════

class TestTrainingHistoryEndpoint:

    def test_returns_200(self, client):
        assert client.get("/api/analytics/training-history").status_code == 200

    def test_has_training_history_key(self, client):
        data = client.get("/api/analytics/training-history").json()
        assert "training_history" in data

    def test_training_history_is_list(self, client):
        data = client.get("/api/analytics/training-history").json()
        assert isinstance(data["training_history"], list)

    def test_training_history_items_have_accuracy(self, client):
        items = client.get("/api/analytics/training-history").json()["training_history"]
        assert len(items) > 0
        for item in items:
            assert "accuracy" in item

    def test_stored_history_returned(self, client, db_session):
        db_session.add(
            TrainingHistory(
                model_version="v1.0",
                epoch=1,
                accuracy=0.88,
                precision=0.87,
                recall=0.85,
                f1_score=0.86,
                train_loss=0.3,
                val_loss=0.35,
                learning_rate=0.001,
                training_samples=500,
                batch_size=32,
            )
        )
        db_session.flush()

        items = client.get("/api/analytics/training-history").json()["training_history"]
        assert any(abs(i["accuracy"] - 0.88) < 0.001 for i in items)


# ════════════════════════════════════════════════════════
# GET /api/analytics/confusion-matrix
# ════════════════════════════════════════════════════════

class TestConfusionMatrixEndpoint:

    def test_returns_200(self, client):
        response = client.get("/api/analytics/confusion-matrix")
        assert response.status_code == 200

    def test_has_confusion_matrix_key(self, client):
        data = client.get("/api/analytics/confusion-matrix").json()
        assert "confusion_matrix" in data

    def test_confusion_matrix_has_tp_tn(self, client):
        cm = client.get("/api/analytics/confusion-matrix").json()["confusion_matrix"]
        for field in ("tp", "tn", "fp", "fn"):
            assert field in cm


# ════════════════════════════════════════════════════════
# GET /api/analytics/feature-importance
# ════════════════════════════════════════════════════════

class TestFeatureImportanceEndpoint:

    def test_returns_200(self, client):
        response = client.get("/api/analytics/feature-importance")
        assert response.status_code == 200

    def test_has_feature_importance_key(self, client):
        data = client.get("/api/analytics/feature-importance").json()
        assert "feature_importance" in data

    def test_features_and_importance_lists(self, client):
        fi = client.get("/api/analytics/feature-importance").json()["feature_importance"]
        assert "features" in fi
        assert "importance" in fi
        assert isinstance(fi["features"], list)
        assert isinstance(fi["importance"], list)
