from pydantic import BaseModel
from typing import List, Optional

class MouseEvent(BaseModel):
    x: int
    y: int
    timestamp: float  # milliseconds

class VerificationRequest(BaseModel):
    session_id: str
    device_fingerprint: str
    user_agent: str
    ip_address: Optional[str] = None
    mouse_events: List[MouseEvent]
    # Additional fields for later
    click_timestamp: Optional[float] = None
    page_url: Optional[str] = None

class VerificationResponse(BaseModel):
    verdict: str  # "human", "bot", "suspicious"
    confidence: float
    layer_triggered: int  # 1 or 2
    reason: str
    risk_score: Optional[float] = None