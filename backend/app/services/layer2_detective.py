import joblib
import numpy as np
import pandas as pd
from app.services.feature_extractor import extract_features_from_events

class Layer2Detective:
    def __init__(self):
        # Load model artifacts
        self.model = joblib.load('/app/app/ml/clickguard_model.pkl')
        self.scaler = joblib.load('/app/app/ml/scaler.pkl')
        self.pt = joblib.load('/app/app/ml/power_transformer.pkl')
        self.feature_cols = joblib.load('/app/app/ml/feature_columns.pkl')
        print("✅ Layer 2 Detective initialized with real model")

    async def analyze(self, mouse_events):
        """
        Analyze mouse events and return verdict.
        """
        # Extract features
        feats = extract_features_from_events(mouse_events)
        if feats is None:
            return {
                "verdict": "human",
                "confidence": 0.5,
                "risk_score": 0.5,
                "reason": "Insufficient data, defaulting to human"
            }

        # Create DataFrame with correct feature order
        X = pd.DataFrame([feats])[self.feature_cols].fillna(0)

        # Apply preprocessing
        X_pt = self.pt.transform(X)
        X_scaled = self.scaler.transform(X_pt)

        # Predict
        proba = self.model.predict_proba(X_scaled)[0]
        pred = self.model.predict(X_scaled)[0]

        verdict = "bot" if proba[1] > 0.5 else "human"
        confidence = float(proba[1] if pred == 1 else proba[0])
        risk_score = float(proba[1])

        return {
            "verdict": verdict,
            "confidence": confidence,
            "risk_score": risk_score,
            "reason": f"ML analysis: risk={risk_score:.2f}"
        }


# Singleton instance
detective = Layer2Detective()