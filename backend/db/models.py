"""Database models for AIOps Platform"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Text, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base  # ✨ ADD THIS
from datetime import datetime
import enum

# ✨ ADD THIS - Define Base declaratively
Base = declarative_base()

# ==================== EXISTING MODELS ====================

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

# ==================== NEW MODELS ====================

class TrainingHistory(Base):
    """Track model training iterations"""
    __tablename__ = "training_history"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Training info
    model_version = Column(String, index=True)
    epoch = Column(Integer)
    
    # Metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    
    # Additional metrics
    train_loss = Column(Float)
    val_loss = Column(Float)
    learning_rate = Column(Float)
    
    # Data info
    training_samples = Column(Integer)
    batch_size = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<TrainingHistory(v={self.model_version}, epoch={self.epoch}, f1={self.f1_score:.3f})>"


class PredictionAnalytics(Base):
    """Track prediction accuracy over time"""
    __tablename__ = "prediction_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Prediction info
    prediction_id = Column(Integer, index=True)
    pipeline_id = Column(String, index=True)
    
    # Prediction vs Reality
    predicted_anomaly = Column(Boolean)
    actual_anomaly = Column(Boolean, nullable=True)  # Null until we know actual
    
    # Metrics
    prediction_confidence = Column(Float)
    false_positive = Column(Boolean, nullable=True)
    false_negative = Column(Boolean, nullable=True)
    
    # Timestamps
    predicted_at = Column(DateTime, default=datetime.now, index=True)
    verified_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<PredictionAnalytics(pipeline={self.pipeline_id}, correct={self.actual_anomaly == self.predicted_anomaly})>"


class SystemMetrics(Base):
    """Track system health and performance"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Performance
    avg_prediction_time_ms = Column(Float)
    avg_request_time_ms = Column(Float)
    
    # System health
    total_predictions = Column(Integer)
    successful_predictions = Column(Integer)
    failed_predictions = Column(Integer)
    
    # Database
    db_size_mb = Column(Float)
    db_query_time_ms = Column(Float)
    
    # Alerts
    alerts_generated = Column(Integer)
    critical_alerts = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return f"<SystemMetrics(predictions={self.total_predictions}, alerts={self.alerts_generated})>"


# ==================== JENKINS INTEGRATION ====================

class JenkinsBuild(Base):
    """Stores Jenkins build data with ML prediction and actual outcome."""
    __tablename__ = "jenkins_builds"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String, index=True, nullable=False)
    build_number = Column(Integer, nullable=False)

    # Raw build info from Jenkins
    status = Column(String)          # SUCCESS | FAILURE | ABORTED | IN_PROGRESS
    duration_ms = Column(Integer)
    build_url = Column(String)
    log_snippet = Column(Text)       # last 2 KB of console log
    is_demo = Column(Boolean, default=False)

    # ML prediction (populated at sync time)
    predicted_failure = Column(Boolean, nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)   # LOW/MEDIUM/HIGH
    risk_score = Column(Float, nullable=True)
    recommendation = Column(Text, nullable=True)

    # Tracking: did the prediction match reality?
    actual_failure = Column(Boolean, nullable=True)   # derived from status
    prediction_correct = Column(Boolean, nullable=True)

    # Timestamps
    build_timestamp = Column(DateTime, nullable=True, index=True)
    synced_at = Column(DateTime, default=datetime.now, index=True)

    def __repr__(self):
        return (
            f"<JenkinsBuild(job={self.job_name!r}, "
            f"#{self.build_number}, status={self.status!r})>"
        )