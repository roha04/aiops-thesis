"""
Combined prediction pipeline
"""

from .anomaly import LogAnomalyDetector
from .forecaster import PipelineFailureForecaster

class AIOpsPredictor:
    def __init__(self):
        self.anomaly_detector = LogAnomalyDetector()
        self.forecaster = PipelineFailureForecaster()
    
    def analyze(self, logs, failure_history=None):
        """
        Combined analysis:
        - Analyze logs for anomalies
        - Forecast future failures
        - Combine into risk score
        """
        
        # 1. Log analysis
        log_result = self.anomaly_detector.predict(logs)
        
        # 2. Failure forecast (if history provided)
        forecast_result = None
        if failure_history:
            forecast_result = self.forecaster.predict_next_hour()
        
        # 3. Calculate combined risk score
        risk_score = log_result.get("confidence", 0) * 0.6
        
        if forecast_result and forecast_result.get("predicted_failures", 0) > 3:
            risk_score += 0.4
        
        # 4. Determine risk level
        if risk_score > 0.7:
            risk_level = "HIGH"
            recommendation = "🔴 CRITICAL: Anomaly detected + high failure forecast. Check logs immediately!"
        elif risk_score > 0.4:
            risk_level = "MEDIUM"
            recommendation = "🟡 WARNING: Elevated risk detected. Monitor closely."
        else:
            risk_level = "LOW"
            recommendation = "🟢 OK: System appears healthy."
        
        return {
            "risk_level": risk_level,
            "score": round(risk_score, 2),
            "recommendation": recommendation,
            "details": {
                "log_anomaly": log_result,
                "failure_forecast": forecast_result
            }
        }
    
    def train(self, logs_list, failure_history):
        """Train both models"""
        self.anomaly_detector.train(logs_list)
        self.forecaster.train(failure_history)