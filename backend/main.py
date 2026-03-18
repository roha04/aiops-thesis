"""
AIOps Platform - Backend
FastAPI server for ML predictions
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AIOps Platform",
    description="AI-Powered Operations for CI/CD Pipeline Monitoring",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== HEALTH CHECK ====================
@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "AIOps Backend",
        "version": "1.0.0"
    }

# ==================== DASHBOARD ====================
@app.get("/api/dashboard")
def dashboard_stats():
    """Get dashboard statistics"""
    return {
        "total_alerts": 0,
        "model_accuracy": 0.873,
        "avg_lead_time": "22 min",
        "anomalies_trend": []
    }

# ==================== PREDICTION ====================
@app.post("/api/predict")
def predict_pipeline(pipeline_id: str):
    """Predict pipeline failure"""
    return {
        "pipeline_id": pipeline_id,
        "prediction": {
            "risk_level": "LOW",
            "score": 0.25,
            "recommendation": "Pipeline is healthy"
        }
    }

# ==================== ALERTS ====================
@app.get("/api/alerts")
def get_alerts(limit: int = 20):
    """Get recent alerts"""
    return {
        "total": 0,
        "alerts": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
