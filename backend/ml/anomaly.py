"""
Log Anomaly Detection using Isolation Forest
"""

from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import os

class LogAnomalyDetector:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.is_trained = False
        self.model_path = "models/anomaly.pkl"
    
    def train(self, logs_list):
        """Train on historical logs"""
        if not logs_list or len(logs_list) < 10:
            print("⚠️ Need at least 10 logs to train")
            return False
        
        try:
            # Convert text to vectors
            X = self.vectorizer.fit_transform(logs_list)
            
            # Train model
            self.model.fit(X)
            self.is_trained = True
            
            # Save model
            os.makedirs("models", exist_ok=True)
            pickle.dump((self.vectorizer, self.model), 
                       open(self.model_path, "wb"))
            print(f"✅ Model trained on {len(logs_list)} logs")
            return True
        except Exception as e:
            print(f"❌ Training error: {e}")
            return False
    
    def load_model(self):
        """Load pre-trained model"""
        try:
            self.vectorizer, self.model = pickle.load(
                open(self.model_path, "rb")
            )
            self.is_trained = True
            print("✅ Model loaded")
            return True
        except:
            print("⚠️ No saved model found")
            return False
    
    def predict(self, log_text):
        """Predict if log text is anomalous"""
        if not self.is_trained:
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "confidence": 0.0,
                "error": "Model not trained"
            }
        
        try:
            X = self.vectorizer.transform([log_text])
            score = self.model.decision_function(X)[0]
            
            return {
                "is_anomaly": score < -0.5,
                "anomaly_score": float(score),
                "confidence": float(abs(score)),
                "error": None
            }
        except Exception as e:
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "confidence": 0.0,
                "error": str(e)
            }