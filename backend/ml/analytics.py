"""
ML Model Analytics and Evaluation
Generates metrics for thesis visualization
"""

import numpy as np
from sklearn.metrics import (
    roc_curve, auc, confusion_matrix, 
    precision_recall_curve, f1_score,
    classification_report
)
from sklearn.preprocessing import label_binarize
import json

class ModelAnalytics:
    """Calculate advanced ML metrics for visualization"""
    
    def __init__(self):
        self.results = {}
    
    def calculate_roc_curve(self, y_true, y_scores):
        """Calculate ROC curve data"""
        try:
            fpr, tpr, thresholds = roc_curve(y_true, y_scores)
            roc_auc = auc(fpr, tpr)
            
            return {
                "fpr": fpr.tolist(),
                "tpr": tpr.tolist(),
                "thresholds": thresholds.tolist(),
                "auc": float(roc_auc)
            }
        except Exception as e:
            print(f"ROC curve error: {e}")
            return None
    
    def calculate_confusion_matrix(self, y_true, y_pred):
        """Calculate confusion matrix"""
        try:
            cm = confusion_matrix(y_true, y_pred)
            
            tn, fp, fn, tp = cm.ravel()
            
            return {
                "matrix": cm.tolist(),
                "tp": int(tp),
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tpr": float(tp / (tp + fn)) if (tp + fn) > 0 else 0,
                "fpr": float(fp / (fp + tn)) if (fp + tn) > 0 else 0,
                "specificity": float(tn / (tn + fp)) if (tn + fp) > 0 else 0
            }
        except Exception as e:
            print(f"Confusion matrix error: {e}")
            return None
    
    def calculate_precision_recall(self, y_true, y_scores):
        """Calculate Precision-Recall curve"""
        try:
            precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
            
            # Calculate F1 for each threshold
            f1_scores = []
            for p, r in zip(precision, recall):
                if (p + r) > 0:
                    f1 = 2 * (p * r) / (p + r)
                else:
                    f1 = 0
                f1_scores.append(f1)
            
            # Average precision
            ap = np.mean(precision)
            
            return {
                "precision": precision.tolist(),
                "recall": recall.tolist(),
                "thresholds": thresholds.tolist(),
                "f1_scores": f1_scores,
                "average_precision": float(ap)
            }
        except Exception as e:
            print(f"Precision-Recall error: {e}")
            return None
    
    def calculate_feature_importance(self, feature_names, importance_scores):
        """Calculate feature importance"""
        try:
            # Normalize scores to 0-100
            min_score = min(importance_scores)
            max_score = max(importance_scores)
            
            if max_score - min_score > 0:
                normalized = [
                    100 * (score - min_score) / (max_score - min_score)
                    for score in importance_scores
                ]
            else:
                normalized = [50] * len(importance_scores)
            
            # Sort by importance
            features_with_importance = list(zip(feature_names, normalized))
            features_with_importance.sort(key=lambda x: x[1], reverse=True)
            
            return {
                "features": [f[0] for f in features_with_importance],
                "importance": [float(f[1]) for f in features_with_importance]
            }
        except Exception as e:
            print(f"Feature importance error: {e}")
            return None
    
    def generate_classification_report(self, y_true, y_pred):
        """Generate classification report"""
        try:
            report = classification_report(y_true, y_pred, output_dict=True)
            return report
        except Exception as e:
            print(f"Classification report error: {e}")
            return None
    
    def compare_models(self, model_results):
        """Compare multiple model versions"""
        try:
            comparison = []
            for model_name, metrics in model_results.items():
                comparison.append({
                    "name": model_name,
                    "accuracy": metrics.get("accuracy", 0),
                    "precision": metrics.get("precision", 0),
                    "recall": metrics.get("recall", 0),
                    "f1_score": metrics.get("f1_score", 0),
                    "auc": metrics.get("auc", 0)
                })
            
            return sorted(comparison, key=lambda x: x["f1_score"], reverse=True)
        except Exception as e:
            print(f"Model comparison error: {e}")
            return None


# Helper function to convert scores to predictions
def get_predictions_from_scores(scores, threshold=0.5):
    """Convert anomaly scores to binary predictions"""
    return [1 if score > threshold else 0 for score in scores]