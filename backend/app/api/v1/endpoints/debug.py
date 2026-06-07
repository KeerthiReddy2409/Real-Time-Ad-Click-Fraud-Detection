from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.services.feature_extractor import extract_features_from_events
from app.services.layer2_detective import detective
import pandas as pd

router = APIRouter(prefix="/debug", tags=["debug"])

class MouseEvent(BaseModel):
    x: int
    y: int
    timestamp: float

class InspectRequest(BaseModel):
    events: List[MouseEvent]

@router.post("/inspect")
async def inspect_mouse_events(payload: InspectRequest):
    events = payload.events  # keep Pydantic objects, not dicts
    feats = extract_features_from_events(events)
    if feats is None:
        return {"error": "Insufficient data", "features": None}

    X = pd.DataFrame([feats])[detective.feature_cols].fillna(0)
    X_pt = detective.pt.transform(X)
    X_scaled = detective.scaler.transform(X_pt)
    proba = detective.model.predict_proba(X_scaled)[0].tolist()
    pred = detective.model.predict(X_scaled)[0]
    return {
        "features": feats,
        "probabilities": {"human": proba[0], "bot": proba[1]},
        "prediction": int(pred)
    }