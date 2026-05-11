"""
Combined prediction pipeline
"""

from .anomaly import LogAnomalyDetector
from .forecaster import PipelineFailureForecaster

class AIOpsPredictor:
    def __init__(self):
        self.anomaly_detector = LogAnomalyDetector()
        self.forecaster = PipelineFailureForecaster()

    def _parse_first_line(self, logs: str) -> dict | None:
        """
        Parse the first non-empty line through Drain so the API can surface
        structured metadata (event id, template, log level, service, params).
        Returns ``None`` if the parser is unavailable.
        """
        if not logs:
            return None
        first_line = next(
            (line for line in logs.splitlines() if line.strip()), logs.strip()
        )
        try:
            parsed = self.anomaly_detector.parse_log(first_line)
        except Exception:
            return None
        return parsed.to_dict() if parsed is not None else None

    def analyze(self, logs, failure_history=None):
        """
        Combined analysis:
        - Parse logs through Drain for structured metadata
        - Analyze logs for anomalies
        - Forecast future failures
        - Combine into risk score
        - Compute SHAP explanation for the line-level prediction
        """

        # 1. Drain parse (returns event_id / template / log_level / service / params)
        parsed_log = self._parse_first_line(logs)

        # 2. Log analysis
        log_result = self.anomaly_detector.predict(logs)

        # 3. Failure forecast (if history provided)
        forecast_result = None
        if failure_history:
            forecast_result = self.forecaster.predict_next_hour()

        # 4. Calculate combined risk score
        risk_score = log_result.get("confidence", 0) * 0.6

        if forecast_result and forecast_result.get("predicted_failures", 0) > 3:
            risk_score += 0.4

        # 5. Determine risk level
        if risk_score > 0.7:
            risk_level = "HIGH"
            recommendation = "🔴 КРИТИЧНО: виявлено аномалію та високий прогноз збоїв. Негайно перевірте логи!"
        elif risk_score > 0.4:
            risk_level = "MEDIUM"
            recommendation = "🟡 УВАГА: виявлено підвищений ризик. Уважно стежте."
        else:
            risk_level = "LOW"
            recommendation = "🟢 OK: система працює нормально."

        # 6. SHAP explanation (graceful no-op until the supervised RF is trained)
        try:
            shap_explanation = self.anomaly_detector.explain(logs, top_k=3)
        except Exception:
            shap_explanation = {}

        return {
            "risk_level": risk_level,
            "score": round(risk_score, 2),
            "recommendation": recommendation,
            "shap_explanation": shap_explanation,
            "parsed_log": parsed_log,
            "details": {
                "log_anomaly": log_result,
                "failure_forecast": forecast_result
            }
        }

    def train(self, logs_list, labels, failure_history):
        """Train both models. labels is a list of 0/1 matching logs_list."""
        self.anomaly_detector.train(logs_list, labels)
        self.forecaster.train(failure_history)