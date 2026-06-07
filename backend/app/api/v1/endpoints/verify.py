from fastapi import APIRouter, Request, Header
from app.models.request import VerificationRequest, VerificationResponse
from app.services.layer1_bouncer import Layer1Bouncer
from app.services.layer2_detective import detective
from app.core.redis_client import redis_client
import json

router = APIRouter()

@router.post("/verify", response_model=VerificationResponse)
async def verify_request(
    payload: VerificationRequest,
    request: Request,
    x_demo_ip: str = Header(None, alias="X-Demo-IP")
):
        # ---- Demo Mode IP override (only for local development) ----
    client_ip = payload.ip_address or request.client.host
    if x_demo_ip:
        client_ip = x_demo_ip
        print(f"🔧 Demo mode: Using fake IP {x_demo_ip}")

    # ---- Layer 1: Hardware Bouncer ----
    allowed, reason = await Layer1Bouncer.analyze(client_ip, payload.device_fingerprint)
    if not allowed:
        final_response = VerificationResponse(
            verdict="bot",
            confidence=0.99,
            layer_triggered=1,
            reason=reason,
            risk_score=0.9
        )
    else:
        # ---- Layer 2: ML Detective ----
        ml_result = await detective.analyze(payload.mouse_events)
        final_response = VerificationResponse(
            verdict=ml_result["verdict"],
            confidence=ml_result["confidence"],
            layer_triggered=2,
            reason=ml_result["reason"],
            risk_score=ml_result["risk_score"]
        )

    # ---- Publish to Redis for live dashboard ----
    try:
        client = redis_client.get_client()
        message = json.dumps({
            "session_id": payload.session_id,
            "ip": client_ip,
            "verdict": final_response.verdict,
            "confidence": final_response.confidence,
            "layer_triggered": final_response.layer_triggered,
            "reason": final_response.reason,
            "risk_score": final_response.risk_score,
            "device_fingerprint": payload.device_fingerprint[:20],
            "mouse_events_count": len(payload.mouse_events)
        })
        await client.publish("clickguard:decisions", message)
    except Exception as e:
        print(f"Redis publish error: {e}")

    return final_response