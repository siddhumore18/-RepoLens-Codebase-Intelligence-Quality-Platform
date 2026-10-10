"""
Anomaly Detector Module
Robust MAD statistics and Isolation Forest ML for code smell identification.
"""

import numpy as np
from typing import List, Dict, Any
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    FEATURE_KEYS = [
        "loc", "cyclomatic_complexity", "cognitive_complexity",
        "max_nesting", "param_count", "halstead_volume",
        "halstead_difficulty", "out_degree"
    ]

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.iso_forest = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=42
        )

    def detect_anomalies(self, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not features:
            return []

        n_samples = len(features)
        enriched_results = [dict(f) for f in features]

        for key in self.FEATURE_KEYS:
            values = np.array([f.get(key, 0.0) for f in features], dtype=float)
            median = float(np.median(values))
            mad = float(np.median(np.abs(values - median)))

            if mad == 0.0:
                q75, q25 = np.percentile(values, [75, 25])
                iqr = q75 - q25
                scale = (iqr / 1.349) if iqr > 0 else 1.0
            else:
                scale = mad

            for i, val in enumerate(values):
                z_robust = 0.6745 * (val - median) / scale if scale > 0 else 0.0
                enriched_results[i][f"{key}_robust_z"] = round(float(z_robust), 3)

        for item in enriched_results:
            pos_z = [max(0.0, min(10.0, item[f"{key}_robust_z"])) for key in self.FEATURE_KEYS]
            item["robust_anomaly_score"] = round(float(np.mean(pos_z)), 3)

        if n_samples >= 5:
            X = np.array([[f.get(k, 0.0) for k in self.FEATURE_KEYS] for f in features])
            self.iso_forest.fit(X)
            anomaly_preds = self.iso_forest.predict(X)
            anomaly_scores = self.iso_forest.decision_function(X)

            min_s, max_s = anomaly_scores.min(), anomaly_scores.max()
            norm_scores = 1.0 - (anomaly_scores - min_s) / (max_s - min_s + 1e-8)

            for i in range(n_samples):
                is_anomaly = bool(anomaly_preds[i] == -1)
                enriched_results[i]["is_ml_anomaly"] = is_anomaly
                enriched_results[i]["ml_anomaly_probability"] = round(float(norm_scores[i]), 3)
                enriched_results[i]["review_priority"] = self._compute_priority(
                    enriched_results[i]["robust_anomaly_score"],
                    enriched_results[i]["ml_anomaly_probability"],
                    enriched_results[i].get("pagerank", 0.0)
                )
        else:
            for item in enriched_results:
                item["is_ml_anomaly"] = item["robust_anomaly_score"] > 2.0
                item["ml_anomaly_probability"] = min(1.0, item["robust_anomaly_score"] / 5.0)
                item["review_priority"] = "HIGH" if item["robust_anomaly_score"] > 2.5 else "MEDIUM" if item["robust_anomaly_score"] > 1.2 else "LOW"

        enriched_results.sort(key=lambda x: (x.get("ml_anomaly_probability", 0), x.get("robust_anomaly_score", 0)), reverse=True)
        return enriched_results

    def _compute_priority(self, robust_z: float, ml_prob: float, pagerank: float) -> str:
        composite = (robust_z * 0.4) + (ml_prob * 4.0 * 0.4) + (pagerank * 100.0 * 0.2)
        if composite > 3.0 or ml_prob > 0.85:
            return "CRITICAL"
        elif composite > 1.8 or ml_prob > 0.65:
            return "HIGH"
        elif composite > 0.9 or ml_prob > 0.45:
            return "MEDIUM"
        else:
            return "LOW"
