"""Generate sample historical data for analytics demonstration"""

from datetime import datetime, timedelta
import random
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from db.config import SessionLocal
from db.models import (
    TrainingHistory, PredictionAnalytics, SystemMetrics, 
    Prediction, Alert
)

def generate_training_history():
    """Generate training history for 5 epochs"""
    print("📚 Generating training history...")
    db = SessionLocal()
    
    # Clear existing
    db.query(TrainingHistory).delete()
    
    for epoch in range(1, 6):
        history = TrainingHistory(
            model_version="v1.0",
            epoch=epoch,
            accuracy=0.80 + (epoch * 0.02),
            precision=0.78 + (epoch * 0.022),
            recall=0.82 + (epoch * 0.018),
            f1_score=0.80 + (epoch * 0.02),
            train_loss=0.5 - (epoch * 0.08),
            val_loss=0.52 - (epoch * 0.075),
            learning_rate=0.001,
            training_samples=1000,
            batch_size=32,
            created_at=datetime.now() - timedelta(days=5-epoch)
        )
        db.add(history)
        print(f"  ✅ Epoch {epoch}: F1={history.f1_score:.3f}, Loss={history.train_loss:.3f}")
    
    db.commit()
    db.close()
    print("✅ Training history generated\n")


def generate_prediction_analytics():
    """Generate 30 days of prediction analytics"""
    print("📈 Generating prediction analytics (30 days)...")
    db = SessionLocal()
    
    # Clear existing
    db.query(PredictionAnalytics).delete()
    
    for day in range(30):
        num_predictions = random.randint(30, 80)
        correct_predictions = int(num_predictions * (0.75 + random.uniform(-0.05, 0.15)))
        
        for pred_num in range(num_predictions):
            is_correct = pred_num < correct_predictions
            
            analytics = PredictionAnalytics(
                prediction_id=day * 100 + pred_num,
                pipeline_id=f"pipeline-{random.randint(1, 5)}",
                predicted_anomaly=random.choice([True, False]),
                actual_anomaly=random.choice([True, False]) if is_correct else random.choice([False, True]),
                prediction_confidence=random.uniform(0.6, 0.99),
                false_positive=None if is_correct else random.choice([True, False]),
                false_negative=None if is_correct else random.choice([True, False]),
                predicted_at=datetime.now() - timedelta(days=30-day) + timedelta(hours=random.randint(0, 23)),
                verified_at=datetime.now() - timedelta(days=30-day) + timedelta(hours=random.randint(0, 23))
            )
            db.add(analytics)
        
        accuracy = (correct_predictions / num_predictions * 100) if num_predictions > 0 else 0
        print(f"  ✅ Day {day+1}: {num_predictions} predictions, {accuracy:.1f}% accuracy")
    
    db.commit()
    db.close()
    print("✅ Prediction analytics generated\n")


def generate_system_metrics():
    """Generate system metrics for last 7 days"""
    print("❤️ Generating system metrics (7 days)...")
    db = SessionLocal()
    
    # Clear existing
    db.query(SystemMetrics).delete()
    
    for day in range(7):
        metrics = SystemMetrics(
            avg_prediction_time_ms=random.uniform(100, 200),
            avg_request_time_ms=random.uniform(200, 400),
            total_predictions=random.randint(500, 1500),
            successful_predictions=random.randint(450, 1400),
            failed_predictions=random.randint(10, 100),
            db_size_mb=random.uniform(100, 500),
            db_query_time_ms=random.uniform(5, 50),
            alerts_generated=random.randint(20, 100),
            critical_alerts=random.randint(5, 20),
            created_at=datetime.now() - timedelta(days=7-day)
        )
        db.add(metrics)
        print(f"  ✅ Day {day+1}: {metrics.total_predictions} predictions, {metrics.alerts_generated} alerts")
    
    db.commit()
    db.close()
    print("✅ System metrics generated\n")


def generate_sample_alerts():
    """Generate sample alerts"""
    print("🚨 Generating sample alerts...")
    db = SessionLocal()
    
    for i in range(20):
        alert = Alert(
            prediction_id=i,
            pipeline_id=f"pipeline-{random.randint(1, 5)}",
            alert_type="ANOMALY",
            severity=random.choice(["WARNING", "CRITICAL"]),
            message=f"Anomaly detected in build pipeline",
            is_resolved=random.choice([True, False]),
            created_at=datetime.now() - timedelta(days=random.randint(0, 30)),
            resolved_at=datetime.now() - timedelta(days=random.randint(0, 30)) if random.choice([True, False]) else None
        )
        db.add(alert)
    
    db.commit()
    db.close()
    print("✅ Sample alerts generated\n")


if __name__ == "__main__":
    print("\n🚀 Generating Sample Historical Data for Analytics\n")
    print("=" * 50)
    
    try:
        generate_training_history()
        generate_prediction_analytics()
        generate_system_metrics()
        generate_sample_alerts()
        
        print("=" * 50)
        print("\n✅ All sample data generated successfully!")
        print("\n📊 Now run the frontend and check the 'History' page!")
        print("   You should see graphs with sample data.\n")
        
    except Exception as e:
        print(f"\n❌ Error generating data: {e}")
        import traceback
        traceback.print_exc()