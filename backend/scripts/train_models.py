"""Train ML models and save metrics"""

import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sqlalchemy.orm import Session
from db.config import SessionLocal, engine
from db.models import TrainingData, ModelMetrics, Base
from ml.anomaly import LogAnomalyDetector
from ml.forecaster import PipelineFailureForecaster
from datetime import datetime

def train_models():
    """Train and evaluate models"""
    
    db = SessionLocal()
    
    try:
        print("🤖 Starting model training...")
        
        # Load training data
        logs = db.query(TrainingData).all()
        
        if not logs or len(logs) < 50:
            print("❌ Not enough training data (need at least 50 samples)")
            return False
        
        print(f"📊 Loaded {len(logs)} training samples")
        
        # Prepare data
        X = [log.log_text for log in logs]
        y = np.array([1 if log.is_anomaly else 0 for log in logs])
        
        # Split: 80% train, 20% test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"   Training samples: {len(X_train)}")
        print(f"   Testing samples: {len(X_test)}")
        
        # ============ TRAIN ANOMALY DETECTOR ============
        print("\n1️⃣  Training Anomaly Detector...")
        detector = LogAnomalyDetector()
        detector.train(X_train)
        
        # Test predictions
        y_pred = np.array([
            1 if detector.predict(log)["is_anomaly"] else 0 
            for log in X_test
        ])
        
        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        print(f"   ✅ Anomaly Detection Metrics:")
        print(f"      Accuracy:  {accuracy:.4f}")
        print(f"      Precision: {precision:.4f}")
        print(f"      Recall:    {recall:.4f}")
        print(f"      F1 Score:  {f1:.4f}")
        
        # Save metrics to database
        metrics = ModelMetrics(
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            test_samples=len(X_test),
            true_positives=int(tp),
            true_negatives=int(tn),
            false_positives=int(fp),
            false_negatives=int(fn),
            training_samples=len(X_train),
            model_version="1.0"
        )
        db.add(metrics)
        db.commit()
        
        # ============ TRAIN FORECASTER ============
        print("\n2️⃣  Training Failure Forecaster...")
        
        # Generate synthetic time series data
        failure_history = [
            0, 1, 0, 2, 1, 5, 3, 2, 1, 0, 2, 4, 3, 1, 2,
            0, 1, 0, 2, 1, 5, 3, 2, 1, 0, 2, 4, 3, 1, 2,
            0, 1, 0, 2, 1, 5, 3, 2, 1, 0
        ]
        
        forecaster = PipelineFailureForecaster()
        forecaster.train(failure_history)
        print(f"   ✅ Forecaster trained on {len(failure_history)} data points")
        
        print("\n✅ Model training completed successfully!")
        print(f"📊 Metrics saved to database")
        
        return True
        
    except Exception as e:
        print(f"❌ Training error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    train_models()