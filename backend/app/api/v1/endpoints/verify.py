from fastapi import APIRouter, Request
from app.models.request import VerificationRequest, VerificationResponse
from app.services.layer1_bouncer import Layer1Bouncer
from app.services.layer2_detective import detective

router = APIRouter()

@router.post("/verify", response_model=VerificationResponse)
async def verify_request(payload: VerificationRequest, request: Request):
    # Get client IP
    client_ip = payload.ip_address or request.client.host

    # Layer 1: Hardware Bouncer
    allowed, reason = await Layer1Bouncer.analyze(client_ip, payload.device_fingerprint)
    if not allowed:
        return VerificationResponse(
            verdict="bot",
            confidence=0.99,
            layer_triggered=1,
            reason=reason,
            risk_score=0.9
        )

    # Layer 2: ML Detective
    ml_result = await detective.analyze(payload.mouse_events)
    return VerificationResponse(
        verdict=ml_result["verdict"],
        confidence=ml_result["confidence"],
        layer_triggered=2,
        reason=ml_result["reason"],
        risk_score=ml_result["risk_score"]
    )