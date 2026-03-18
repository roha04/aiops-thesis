"""
AIOps Platform - FastAPI Backend
ML-powered CI/CD monitoring
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging

# Import ML models
from ml.pipeline import AIOpsPredictor

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="🤖 AIOps Platform",
    description="AI-Powered Operations for CI/CD Pipeline Monitoring",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ML predictor
predictor = AIOpsPredictor()

# ==================== HEALTH CHECK ====================

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AIOps Backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# ==================== PREDICTION ====================

@app.post("/api/predict")
def predict_pipeline(pipeline_id: str, logs: str = ""):
    """
    Predict if pipeline will fail
    
    Example:
    POST /api/predict?pipeline_id=jenkins-build-123&logs=ERROR timeout in DB
    """
    try:
        if not logs:
            logs = f"Build log from {pipeline_id}"
        
        # Mock failure history (in real app, fetch from DB)
        failure_history = [0, 1, 0, 2, 1, 5, 3, 2, 1]
        
        # Get prediction
        result = predictor.analyze(logs, failure_history)
        
        return {
            "pipeline_id": pipeline_id,
            "timestamp": datetime.now().isoformat(),
            "prediction": result
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DASHBOARD ====================

@app.get("/api/dashboard")
def dashboard_stats():
    """Get dashboard statistics"""
    # Mock data - replace with real data from Elasticsearch/DB
    return {
        "total_alerts": 12,
        "model_accuracy": 0.873,
        "avg_lead_time": "22 min",
        "critical_issues": 3,
        "anomalies_trend": [
            {"date": "Mon", "count": 4},
            {"date": "Tue", "count": 3},
            {"date": "Wed", "count": 7},
            {"date": "Thu", "count": 2},
            {"date": "Fri", "count": 5},
            {"date": "Sat", "count": 3},
            {"date": "Sun", "count": 2},
        ]
    }

# ==================== ALERTS ====================

@app.get("/api/alerts")
def get_alerts(limit: int = 20):
    """Get recent alerts"""
    # Mock data - replace with real data from Elasticsearch
    return [
        {
            "_id": "1",
            "_source": {
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "pipeline_id": "jenkins-build-125",
                "anomaly_score": -0.87,
                "log_snippet": "ERROR: Database connection timeout",
                "is_anomaly": True
            }
        },
        {
            "_id": "2",
            "_source": {
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "pipeline_id": "jenkins-build-124",
                "anomaly_score": -0.62,
                "log_snippet": "WARNING: Memory usage spike detected",
                "is_anomaly": True
            }
        }
    ]

# ==================== TRAINING ====================

@app.post("/api/train")
def train_models(logs_count: int = 100):
    """Retrain ML models (admin endpoint)"""
    try:
        # Mock training data
        mock_logs = [
            "ERROR: Database timeout",
            "WARNING: Memory spike",
            "INFO: Build started",
            "ERROR: Test failed",
        ] * 25
        
        mock_failure_history = [0, 1, 0, 2, 1, 5, 3, 2, 1] * 11
        
        predictor.train(mock_logs, mock_failure_history)
        
        return {
            "status": "success",
            "message": "Models retrained",
            "logs_used": len(mock_logs),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== STARTUP ====================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🤖 AIOps Backend Starting...")
    
    # Try to load trained models
    loaded = predictor.anomaly_detector.load_model()
    if not loaded:
        logger.warning("No trained model found. Run /api/train first.")
    
    logger.info("✅ Backend Ready!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",  # Import string for reload to work
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )