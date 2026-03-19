"""Request/Response Schemas - Data Validation"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ==================== ANALYTICS ====================

class AnalyticsSummary(BaseModel):
    total_predictions: int
    total_anomalies: int
    anomaly_rate: float
    total_alerts: int
    model_accuracy: float
    model_f1: float
    test_samples: int

class ROCCurve(BaseModel):
    fpr: List[float]
    tpr: List[float]
    auc: float
    thresholds: List[float]

class ConfusionMatrix(BaseModel):
    tp: int
    tn: int
    fp: int
    fn: int
    tpr: float
    fpr: float
    specificity: float

class PrecisionRecall(BaseModel):
    precision: List[float]
    recall: List[float]
    f1_scores: List[float]
    average_precision: float

class FeatureImportance(BaseModel):
    features: List[str]
    importance: List[float]

class ModelVersion(BaseModel):
    version: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float

# ==================== PREDICTIONS ====================

class PredictionRequest(BaseModel):
    pipeline_id: str
    logs: Optional[str] = ""

class PredictionResponse(BaseModel):
    id: int
    pipeline_id: str
    risk_level: str
    anomaly_score: float
    predicted_failures: int
    created_at: datetime

class AnomalyTrend(BaseModel):
    date: str
    count: int

class DashboardStats(BaseModel):
    total_alerts: int
    model_accuracy: float
    avg_lead_time: str
    critical_issues: int
    anomalies_trend: List[AnomalyTrend]

# ==================== ALERTS ====================

class AlertSource(BaseModel):
    timestamp: str
    pipeline_id: str
    severity: str
    message: str
    is_resolved: bool

class Alert(BaseModel):
    _id: str
    _source: AlertSource

# ==================== METRICS ====================

class MetricsResponse(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    test_samples: int
    true_positives: int
    false_positives: int
    model_version: str
    trained_at: datetime

class TrainingResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime