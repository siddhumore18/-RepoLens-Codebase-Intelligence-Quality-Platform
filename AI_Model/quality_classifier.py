"""
Quality Classifier Module
Supervised Machine Learning model for code smell and refactoring urgency estimation.
"""

import numpy as np
from typing import List, Dict, Any
from sklearn.ensemble import GradientBoostingRegressor

class CodeQualityClassifier:
    FEATURE_NAMES = [
        "loc", "cyclomatic_complexity", "cognitive_complexity",
        "max_nesting", "param_count", "halstead_volume",
        "halstead_difficulty", "in_degree", "out_degree", "pagerank"
    ]

    def __init__(self):
        self.regressor = GradientBoostingRegressor(
            n_estimators=80,
            max_depth=3,
            learning_rate=0.1,
            random_state=42
        )
        self.is_trained = False
        self._init_synthetic_weights()

    def _init_synthetic_weights(self):
        np.random.seed(42)
        n_samples = 400
        
        loc = np.random.exponential(scale=35, size=n_samples) + 5
        cyclomatic = np.random.poisson(lam=4, size=n_samples) + 1
        cognitive = cyclomatic * np.random.uniform(1.0, 2.5, size=n_samples)
        nesting = np.random.poisson(lam=2, size=n_samples) + 1
        params = np.random.poisson(lam=2, size=n_samples)
        volume = loc * np.random.uniform(15, 30, size=n_samples)
        difficulty = np.random.uniform(2, 25, size=n_samples)
        in_deg = np.random.poisson(lam=2, size=n_samples)
        out_deg = np.random.poisson(lam=3, size=n_samples)
        pagerank = np.random.uniform(0.001, 0.05, size=n_samples)

        X_synth = np.column_stack([
            loc, cyclomatic, cognitive, nesting, params,
            volume, difficulty, in_deg, out_deg, pagerank
        ])

        y_synth = (
            (loc / 80.0) * 0.25 +
            (cyclomatic / 15.0) * 0.25 +
            (cognitive / 20.0) * 0.25 +
            (nesting / 5.0) * 0.15 +
            (out_deg / 10.0) * 0.10
        )
        y_synth = np.clip(y_synth + np.random.normal(0, 0.05, size=n_samples), 0.0, 1.0)

        self.regressor.fit(X_synth, y_synth)
        self.is_trained = True

    def predict_risk(self, feature_dicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not feature_dicts:
            return []

        X = np.array([[f.get(k, 0.0) for k in self.FEATURE_NAMES] for f in feature_dicts])
        raw_preds = self.regressor.predict(X)
        preds = np.clip(raw_preds, 0.0, 1.0)
        importances = dict(zip(self.FEATURE_NAMES, self.regressor.feature_importances_))

        results = []
        for i, f in enumerate(feature_dicts):
            risk_score = round(float(preds[i]), 3)
            
            contributions = {}
            for k in self.FEATURE_NAMES:
                val = f.get(k, 0.0)
                weight = importances.get(k, 0.1)
                contributions[k] = val * weight

            top_factor = max(contributions.items(), key=lambda x: x[1])[0]

            results.append({
                "symbol_id": f.get("symbol_id"),
                "name": f.get("name"),
                "file_path": f.get("file_path"),
                "refactoring_urgency": risk_score,
                "primary_risk_driver": top_factor,
                "global_feature_importances": {k: round(float(v), 3) for k, v in importances.items()}
            })

        return results
