"""
Pipeline Failure Forecasting using ARIMA
"""

from statsmodels.tsa.arima.model import ARIMA
import numpy as np

class PipelineFailureForecaster:
    def __init__(self):
        self.model = None
        self.is_trained = False
    
    def train(self, failure_counts_per_hour):
        """
        Train ARIMA model on failure history
        failure_counts_per_hour: [0, 1, 0, 2, 1, 5, 3, ...]
        """
        if not failure_counts_per_hour or len(failure_counts_per_hour) < 10:
            print("⚠️ Need at least 10 data points")
            return False
        
        try:
            # Clean data
            data = [int(x) for x in failure_counts_per_hour if x >= 0]
            
            # Train ARIMA model
            # order=(1,1,1) = (AR, differencing, MA)
            self.model = ARIMA(data, order=(1, 1, 1))
            self.model = self.model.fit()
            self.is_trained = True
            print("✅ Forecaster trained")
            return True
        except Exception as e:
            print(f"❌ Training error: {e}")
            return False
    
    def predict_next_hour(self):
        """Predict failures for next hour"""
        if not self.is_trained:
            return {
                "predicted_failures": 0,
                "upper_bound": 0,
                "lower_bound": 0,
                "error": "Model not trained"
            }
        
        try:
            forecast = self.model.get_forecast(steps=1)
            conf_int = forecast.conf_int()
            
            return {
                "predicted_failures": max(0, int(forecast.predicted_mean[0])),
                "upper_bound": max(0, int(conf_int.iloc[0, 1])),
                "lower_bound": max(0, int(conf_int.iloc[0, 0])),
                "error": None
            }
        except Exception as e:
            return {
                "predicted_failures": 0,
                "upper_bound": 0,
                "lower_bound": 0,
                "error": str(e)
            }