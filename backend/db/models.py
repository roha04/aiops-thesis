"""Database models"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class TrainingData(Base):
    """Training logs for ML models"""
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    log_text = Column(Text)
    is_anomaly = Column(Boolean)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<TrainingData(id={self.id}, anomaly={self.is_anomaly})>"

class Prediction(Base):
    """ML predictions on logs"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(String, index=True)
    log_snippet = Column(Text)
    
    # Anomaly detection results
    is_anomaly = Column(Boolean)
    anomaly_score = Column(Float)
    anomaly_confidence = Column(Float)
    
    # Forecasting results
    predicted_failures = Column(Integer)
    failure_upper_bound = Column(Integer)
    failure_lower_bound = Column(Integer)
    
    # Risk assessment
    risk_level = Column(String)  # LOW, MEDIUM, HIGH
    risk_score = Column(Float)
    recommendation = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<Prediction(pipeline={self.pipeline_id}, risk={self.risk_level})>"

class Alert(Base):
    """Generated alerts from anomalies"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, index=True)
    pipeline_id = Column(String, index=True)
    
    # Alert info
    alert_type = Column(String)  # ANOMALY, FORECAST, BOTH
    severity = Column(String)  # INFO, WARNING, CRITICAL
    message = Column(Text)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Alert(id={self.id}, severity={self.severity})>"

class ModelMetrics(Base):
    """Track model performance over time"""
    __tablename__ = "model_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    
    # Testing info
    test_samples = Column(Integer)
    true_positives = Column(Integer)
    true_negatives = Column(Integer)
    false_positives = Column(Integer)
    false_negatives = Column(Integer)
    
    # Training info
    training_samples = Column(Integer)
    model_version = Column(String)
    
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<ModelMetrics(f1={self.f1_score:.2f})>"