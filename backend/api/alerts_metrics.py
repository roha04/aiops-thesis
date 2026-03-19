"""Alerts & Metrics Endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from db.config import get_db  # ✨ Changed
from db.models import Alert, ModelMetrics  # ✨ Changed

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["operations"])

# ==================== ALERTS ====================

@router.get("/alerts")
def get_alerts(limit: int = 20, db: Session = Depends(get_db)):
    """Get recent alerts"""
    try:
        logger.info(f"🚨 Fetching {limit} alerts...")
        
        alerts = db.query(Alert).order_by(
            Alert.created_at.desc()
        ).limit(limit).all()

        result = []
        for alert in alerts:
            result.append({
                "_id": str(alert.id),
                "_source": {
                    "timestamp": alert.created_at.isoformat(),
                    "pipeline_id": alert.pipeline_id,
                    "severity": alert.severity,
                    "message": alert.message,
                    "is_resolved": alert.is_resolved
                }
            })

        logger.info(f"✅ Fetched {len(result)} alerts")
        return result
        
    except Exception as e:
        logger.error(f"❌ Alerts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== METRICS ====================

@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """Get model performance metrics"""
    try:
        logger.info("📈 Fetching model metrics...")
        
        latest = db.query(ModelMetrics).order_by(
            ModelMetrics.created_at.desc()
        ).first()

        if not latest:
            logger.warning("⚠️ No metrics found, returning defaults")
            return {
                "accuracy": 0.85,
                "precision": 0.82,
                "recall": 0.88,
                "f1_score": 0.85,
                "message": "No metrics available. Run training first."
            }

        result = {
            "accuracy": float(latest.accuracy),
            "precision": float(latest.precision),
            "recall": float(latest.recall),
            "f1_score": float(latest.f1_score),
            "test_samples": latest.test_samples,
            "true_positives": latest.true_positives,
            "false_positives": latest.false_positives,
            "model_version": latest.model_version,
            "trained_at": latest.created_at.isoformat()
        }
        
        logger.info(f"✅ Metrics fetched: Acc={result['accuracy']:.3f}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))