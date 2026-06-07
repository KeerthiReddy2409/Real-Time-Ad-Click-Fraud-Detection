from fastapi import APIRouter, HTTPException
from app.core.redis_client import redis_client
from app.services.feature_extractor import extract_features_from_events
from app.models.request import MouseEvent
import json

router = APIRouter(prefix="/forensics", tags=["forensics"])

@router.get("/recent")
async def recent_sessions():
    client = redis_client.get_client()
    sessions = []
    async for key in client.scan_iter(match="session:*"):
        data = await client.hgetall(key)
        if data:
            sessions.append({
                "session_id": key.replace("session:", ""),
                "ip": data.get("demo_ip", ""),
                "verdict": data.get("verdict", ""),
                "layer": data.get("layer", "?")
            })
    return {"sessions": sessions}

@router.get("/{session_id}")
async def get_session_forensics(session_id: str):
    client = redis_client.get_client()
    data = await client.hgetall(f"session:{session_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    events = json.loads(data["events_json"])
    mouse_events = [MouseEvent(**e) for e in events]
    features = extract_features_from_events(mouse_events)
    
    return {
        "session_id": session_id,
        "ip": data["demo_ip"],
        "device": data["device"],
        "verdict": data["verdict"],
        "layer": data["layer"],
        "reason": data["reason"],
        "features": features,
        "events": events,
        "vpn": data.get("vpn", "false") == "True"
    }