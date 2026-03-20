"""Debug script to check database contents"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db.config import SessionLocal
from db.models import (
    TrainingHistory, PredictionAnalytics, SystemMetrics, Alert, Prediction
)

db = SessionLocal()

print("\n" + "="*50)
print("🔍 DATABASE CONTENTS CHECK")
print("="*50 + "\n")

# Check TrainingHistory
training_count = db.query(TrainingHistory).count()
print(f"📚 TrainingHistory records: {training_count}")
if training_count > 0:
    history = db.query(TrainingHistory).first()
    print(f"   Sample: epoch={history.epoch}, f1={history.f1_score}, created={history.created_at}")
else:
    print("   ⚠️ NO DATA FOUND")

# Check PredictionAnalytics
analytics_count = db.query(PredictionAnalytics).count()
print(f"\n📈 PredictionAnalytics records: {analytics_count}")
if analytics_count > 0:
    analytics = db.query(PredictionAnalytics).first()
    print(f"   Sample: pipeline={analytics.pipeline_id}, confidence={analytics.prediction_confidence}")
else:
    print("   ⚠️ NO DATA FOUND")

# Check SystemMetrics
metrics_count = db.query(SystemMetrics).count()
print(f"\n❤️ SystemMetrics records: {metrics_count}")
if metrics_count > 0:
    metrics = db.query(SystemMetrics).first()
    print(f"   Sample: predictions={metrics.total_predictions}, time_ms={metrics.avg_prediction_time_ms}")
else:
    print("   ⚠️ NO DATA FOUND")

# Check Alerts
alert_count = db.query(Alert).count()
print(f"\n🚨 Alert records: {alert_count}")
if alert_count > 0:
    alert = db.query(Alert).first()
    print(f"   Sample: pipeline={alert.pipeline_id}, severity={alert.severity}")
else:
    print("   ⚠️ NO DATA FOUND")

# Check Predictions (existing)
pred_count = db.query(Prediction).count()
print(f"\n🔮 Prediction records: {pred_count}")

print("\n" + "="*50 + "\n")
db.close()