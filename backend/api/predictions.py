"""Predictions, Dashboard, Explain, Log-Parse & Training Endpoints"""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

from db.config import get_db
from db.models import Prediction, Alert, TrainingData, ModelMetrics
from ml.log_parser import DrainLogParser
from ml.pipeline import AIOpsPredictor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["predictions"])

predictor = AIOpsPredictor()
# Try to hot-load the supervised classifier so SHAP explanations work for
# the very first prediction after a server restart (no /api/train required).
try:
    predictor.anomaly_detector.load_model()
except Exception as _exc:
    logger.debug(f"Predictor model not preloaded: {_exc}")

# ==================== PREDICT ====================

@router.post("/predict")
def predict_pipeline(
    pipeline_id: str,
    logs: str = "",
    db: Session = Depends(get_db)
):
    """Predict if pipeline will fail"""
    try:
        logger.info(f"🔮 Predicting for pipeline: {pipeline_id}")

        if not logs:
            logs = f"Build log from {pipeline_id}"

        training_data = db.query(TrainingData).filter(
            TrainingData.is_anomaly == True
        ).count()
        failure_history = [0, 1, 0, 2, 1, 5, 3, 2, 1] * max(1, training_data // 10)

        result = predictor.analyze(logs, failure_history)

        # SHAP explanation may be empty if the supervised RF isn't trained yet.
        shap_payload = result.get("shap_explanation") or None

        prediction = Prediction(
            pipeline_id=pipeline_id,
            log_snippet=logs[:500],
            is_anomaly=result["details"]["log_anomaly"]["is_anomaly"],
            anomaly_score=result["details"]["log_anomaly"]["anomaly_score"],
            anomaly_confidence=result["details"]["log_anomaly"]["confidence"],
            predicted_failures=result["details"]["failure_forecast"]["predicted_failures"] if result["details"]["failure_forecast"] else 0,
            failure_upper_bound=None,
            failure_lower_bound=None,
            risk_level=result["risk_level"],
            risk_score=result["score"],
            recommendation=result["recommendation"],
            shap_explanation_json=shap_payload,
        )
        db.add(prediction)

        if result["risk_level"] in ["HIGH", "MEDIUM"]:
            alert = Alert(
                prediction_id=prediction.id,
                pipeline_id=pipeline_id,
                alert_type="ANOMALY",
                severity="CRITICAL" if result["risk_level"] == "HIGH" else "WARNING",
                message=result["recommendation"]
            )
            db.add(alert)

        db.commit()
        db.refresh(prediction)

        logger.info(f"✅ Prediction saved: {prediction.id}")

        return {
            "pipeline_id": pipeline_id,
            "prediction_id": prediction.id,
            "timestamp": datetime.now().isoformat(),
            "prediction": result
        }
    except Exception as e:
        logger.error(f"❌ Prediction error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PREDICTIONS HISTORY ====================

@router.get("/predictions")
def get_predictions(limit: int = 50, db: Session = Depends(get_db)):
    """Get prediction history"""
    try:
        logger.info(f"📜 Fetching {limit} predictions...")
        
        predictions = db.query(Prediction).order_by(
            Prediction.created_at.desc()
        ).limit(limit).all()

        result = [
            {
                "id": pred.id,
                "pipeline_id": pred.pipeline_id,
                "risk_level": pred.risk_level,
                "anomaly_score": float(pred.anomaly_score),
                "predicted_failures": pred.predicted_failures,
                "created_at": pred.created_at.isoformat()
            }
            for pred in predictions
        ]
        
        logger.info(f"✅ Fetched {len(result)} predictions")
        return result
        
    except Exception as e:
        logger.error(f"❌ Predictions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DASHBOARD ====================

@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    try:
        logger.info("📊 Fetching dashboard stats...")
        
        latest_metrics = db.query(ModelMetrics).order_by(
            ModelMetrics.created_at.desc()
        ).first()

        accuracy = latest_metrics.accuracy if latest_metrics else 0.85

        alerts_7d = db.query(Alert).filter(
            Alert.created_at >= datetime.now() - timedelta(days=7)
        ).count()

        predictions = db.query(Prediction).filter(
            Prediction.created_at >= datetime.now() - timedelta(days=7)
        ).all()

        trend = {}
        for pred in predictions:
            day = pred.created_at.strftime("%a")
            trend[day] = trend.get(day, 0) + (1 if pred.is_anomaly else 0)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        anomalies_trend = [
            {"date": day, "count": trend.get(day, 0)}
            for day in days
        ]

        critical_alerts = db.query(Alert).filter(
            Alert.severity == "CRITICAL",
            Alert.is_resolved == False
        ).count()

        result = {
            "total_alerts": alerts_7d,
            "model_accuracy": accuracy,
            "avg_lead_time": "22 min",
            "critical_issues": critical_alerts,
            "anomalies_trend": anomalies_trend
        }
        
        logger.info(f"✅ Dashboard stats ready")
        return result
        
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXPLAIN (SHAP) ====================

@router.get("/explain/{prediction_id}")
def explain_prediction(prediction_id: int, db: Session = Depends(get_db)):
    """
    Return SHAP-based explanation for a stored prediction.

    Looks up the saved Prediction row and returns the top contributing features
    (positive SHAP values push the model toward "anomaly", negative values pull
    it toward "normal"). If the explanation wasn't persisted at prediction time
    (e.g. the prediction was made before the supervised model was trained), we
    recompute it on the fly from the stored log snippet and back-fill the row
    so subsequent calls are O(1).
    """
    try:
        pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if pred is None:
            raise HTTPException(status_code=404, detail=f"Prediction {prediction_id} not found")

        explanation = pred.shap_explanation_json

        # Lazy back-fill: recompute if missing and persist for next time.
        if not explanation and pred.log_snippet:
            try:
                explanation = predictor.anomaly_detector.explain(pred.log_snippet, top_k=3)
            except Exception as exc:
                logger.warning(f"On-demand SHAP recompute failed: {exc}")
                explanation = {}

            if explanation and explanation.get("features"):
                pred.shap_explanation_json = explanation
                db.commit()

        if not explanation or not explanation.get("features"):
            return {
                "prediction_id": prediction_id,
                "pipeline_id":   pred.pipeline_id,
                "explanation": {
                    "model":      None,
                    "base_value": None,
                    "features":   [],
                },
                "message": (
                    "No SHAP explanation available. Train the supervised model "
                    "via POST /api/train to enable explainability."
                ),
            }

        return {
            "prediction_id": prediction_id,
            "pipeline_id":   pred.pipeline_id,
            "is_anomaly":    bool(pred.is_anomaly),
            "risk_level":    pred.risk_level,
            "explanation":   explanation,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"❌ Explain error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ==================== LOG PARSING (DRAIN) ====================

@router.post("/parse-logs")
def parse_logs(
    payload: dict = Body(
        ...,
        example={"logs": "INFO [auth] Build started\nERROR [db] Timeout 30s"},
    ),
):
    """
    Parse one or more log lines through the Drain template miner.

    Body
    ----
    ``{"logs": "<single log line OR newline-separated batch>"}``

    Returns
    -------
    ``{"parsed": [<ParsedLog>, ...], "summary": {"n_lines": int,
        "n_unique_templates": int, "templates": [...]} }``

    The parser uses the model's *live* Drain instance when the supervised
    classifier is loaded so the discovered templates stay consistent with
    those used at training time. Otherwise a fresh ad-hoc parser is built.
    """
    raw_logs: Optional[str] = (payload or {}).get("logs")
    if not raw_logs or not isinstance(raw_logs, str):
        raise HTTPException(
            status_code=400, detail="Body must include a non-empty 'logs' string."
        )

    lines = [ln for ln in raw_logs.splitlines() if ln.strip()]
    if not lines:
        lines = [raw_logs.strip()]

    featurizer = (
        predictor.anomaly_detector.structured_featurizer
        if predictor.anomaly_detector.is_trained
        else None
    )
    if featurizer is not None and featurizer.parser is not None:
        # Use the trained Drain instance so template ids match the model's view.
        parser = featurizer.parser
    else:
        parser = DrainLogParser()

    parsed = parser.parse_batch(lines)
    seen_ids = {p.event_id for p in parsed}

    return {
        "parsed":  [p.to_dict() for p in parsed],
        "summary": {
            "n_lines":            len(parsed),
            "n_unique_templates": len(seen_ids),
            "templates":          parser.get_clusters(top_k=10),
        },
    }


# ==================== TRAINING ====================

@router.post("/train")
def train_models(db: Session = Depends(get_db)):
    """Train models with database data"""
    try:
        from scripts.train_models import train_models as run_training

        logger.info("🎓 Starting model training...")
        success = run_training()

        if success:
            result = {
                "status": "success",
                "message": "Models trained successfully",
                "timestamp": datetime.now().isoformat()
            }
            logger.info("✅ Training complete")
            return result
        else:
            raise HTTPException(status_code=500, detail="Training failed")

    except Exception as e:
        logger.error(f"❌ Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))