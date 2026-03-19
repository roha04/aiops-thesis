def get_recent_predictions(self, limit=1000):
    """Fetch recent predictions from Elasticsearch"""
    try:
        query = {
            "size": limit,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {"match_all": {}}
        }
        result = self.es.search(index="predictions", body=query)
        
        predictions = []
        for hit in result['hits']['hits']:
            predictions.append(hit['_source'])
        
        return predictions
    except Exception as e:
        print(f"Error fetching predictions: {e}")
        return []

def get_recent_alerts(self, limit=50):
    """Fetch recent alerts"""
    try:
        query = {
            "size": limit,
            "sort": [{"timestamp": {"order": "desc"}}],
            "query": {"match_all": {}}
        }
        result = self.es.search(index="alerts", body=query)
        
        alerts = []
        for hit in result['hits']['hits']:
            alerts.append(hit['_source'])
        
        return alerts
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return []

def acknowledge_alert(self, alert_id: str):
    """Acknowledge an alert"""
    try:
        self.es.update(
            index="alerts",
            id=alert_id,
            body={"doc": {"acknowledged": True}}
        )
        return True
    except Exception as e:
        print(f"Error acknowledging alert: {e}")
        return False