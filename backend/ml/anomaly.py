"""
Log Anomaly Detection using Hybrid Approach
- Keyword-based + Statistical
"""

import re
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import os

class LogAnomalyDetector:
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.is_trained = False
        self.model_path = "models/anomaly.pkl"
        
        # Error keywords that strongly indicate anomalies
        self.error_keywords = [
            r'ERROR', r'FATAL', r'CRITICAL', r'EXCEPTION',
            r'FAILED', r'TIMEOUT', r'CRASH', r'PANIC',
            r'OutOfMemory', r'StackOverflow', r'NullPointer',
            r'connection.*refused', r'connection.*lost', r'connection.*timeout',
            r'permission denied', r'unauthorized', r'forbidden',
            r'cannot.*find', r'not.*found', r'does.*not.*exist',
            r'disk.*full', r'out.*of.*space', r'limit.*exceeded',
            r'circuit.*breaker', r'unavailable', r'degraded'
        ]
        
        # Compile patterns
        self.error_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.error_keywords]
    
    def _extract_features(self, log_text):
        """Extract numerical features from log text"""
        features = {
            'has_error_keyword': 0,
            'error_keyword_count': 0,
            'has_warning': 0,
            'has_info': 0,
            'log_length': len(log_text),
            'special_char_ratio': 0,
            'number_count': 0,
        }
        
        # Check for error keywords
        error_count = 0
        for pattern in self.error_patterns:
            matches = pattern.findall(log_text)
            error_count += len(matches)
        
        features['error_keyword_count'] = error_count
        features['has_error_keyword'] = 1 if error_count > 0 else 0
        
        # Check for WARNING keyword
        features['has_warning'] = 1 if re.search(r'WARNING', log_text, re.IGNORECASE) else 0
        
        # Check for INFO keyword
        features['has_info'] = 1 if re.search(r'INFO', log_text, re.IGNORECASE) else 0
        
        # Count special characters
        special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', log_text))
        features['special_char_ratio'] = special_chars / max(len(log_text), 1)
        
        # Count numbers
        features['number_count'] = len(re.findall(r'\d+', log_text))
        
        return list(features.values())
    
    def train(self, logs_list):
        """Train on historical logs"""
        if not logs_list or len(logs_list) < 10:
            print("⚠️ Need at least 10 logs to train")
            return False
        
        try:
            # Extract features for all logs
            X = [self._extract_features(log) for log in logs_list]
            
            print(f"   Extracted features from {len(logs_list)} logs")
            print(f"   Feature vector size: 7")
            
            # Train Isolation Forest on features
            self.model = IsolationForest(
                contamination=0.25,  # Expect ~25% anomalies
                random_state=42,
                n_estimators=100
            )
            self.model.fit(X)
            self.is_trained = True
            
            # Save model
            os.makedirs("models", exist_ok=True)
            pickle.dump(self.model, open(self.model_path, "wb"))
            print(f"✅ Model trained on {len(logs_list)} logs")
            
            return True
        except Exception as e:
            print(f"❌ Training error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_model(self):
        """Load pre-trained model"""
        try:
            self.model = pickle.load(open(self.model_path, "rb"))
            self.is_trained = True
            print("✅ Model loaded")
            return True
        except:
            print("⚠️ No saved model found")
            return False
    
    def predict(self, log_text):
        """Predict if log text is anomalous"""
        try:
            # ============ SIMPLE KEYWORD CHECK (HIGH CONFIDENCE) ============
            error_count = 0
            for pattern in self.error_patterns:
                error_count += len(pattern.findall(log_text))
            
            # If has ERROR/FATAL/CRITICAL - it's likely an anomaly
            if error_count >= 1:
                confidence = min(0.95, 0.5 + (0.1 * error_count))
                return {
                    "is_anomaly": True,
                    "anomaly_score": -0.8 * error_count,
                    "confidence": confidence,
                    "reason": f"Detected {error_count} error keyword(s)",
                    "error": None
                }
            
            # ============ ML MODEL FOR MARGINAL CASES ============
            if self.is_trained:
                features = self._extract_features(log_text)
                prediction = self.model.predict([features])[0]
                score = self.model.decision_function([features])[0]
                
                is_anomaly = prediction == -1
                confidence = abs(score) / 2.0
                confidence = min(1.0, max(0.0, confidence))
                
                # Only trust ML if has some warning signals
                if is_anomaly and (
                    re.search(r'WARNING', log_text, re.IGNORECASE) or
                    len(log_text) > 200 or
                    error_count > 0
                ):
                    return {
                        "is_anomaly": True,
                        "anomaly_score": float(score),
                        "confidence": confidence,
                        "reason": "Statistical anomaly detected",
                        "error": None
                    }
            
            # Default: Normal log
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "confidence": 0.9,
                "reason": "Log appears normal",
                "error": None
            }
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return {
                "is_anomaly": False,
                "anomaly_score": 0.0,
                "confidence": 0.0,
                "error": str(e)
            }