"""
AIOps Platform - FastAPI Backend
ML-powered CI/CD monitoring with Database
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from dotenv import load_dotenv
from datetime import datetime

# Import ML models & Database
from ml.pipeline import AIOpsPredictor
from db.config import engine
from db.models import Base

# Import API routers
from api import analytics, predictions, alerts_metrics, analytics_history, jenkins  # ✨ Add this


# ==================== SETUP ====================

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
Base.metadata.create_all(bind=engine)

# Initialize ML predictor
predictor = AIOpsPredictor()

# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    logger.info("🤖 AIOps Backend Starting...")
    
    try:
        loaded = predictor.anomaly_detector.load_model()
        if not loaded:
            logger.warning("⚠️ No trained model found. Run /api/train first.")
    except Exception as e:
        logger.warning(f"Could not load model: {e}")
    
    logger.info("✅ Backend Ready!")
    
    yield
    
    logger.info("🛑 Backend Shutting Down...")

# ==================== APP INITIALIZATION ====================

app = FastAPI(
    title="🤖 AIOps Platform",
    description="AI-Powered Operations for CI/CD Pipeline Monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "127.0.0.1"],
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
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# ==================== INCLUDE ROUTERS ====================

app.include_router(analytics.router)          # /api/analytics/*
app.include_router(predictions.router)        # /api/predict, /api/predictions, /api/dashboard, /api/train
app.include_router(alerts_metrics.router)     # /api/alerts, /api/metrics
app.include_router(analytics_history.router)  # ✨ Add this
app.include_router(jenkins.router)            # /api/jenkins/*

# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
