from fastapi import APIRouter
from app.core.redis_client import redis_client

router = APIRouter(prefix="/admin", tags=["admin"])
BLACKLIST_SET_KEY = "demo:blacklisted_ips"
@router.post("/blacklist-ip")
async def blacklist_ip(ip: str):
    await redis_client.add_to_blacklist(ip)
    return {"status": "blacklisted", "ip": ip}

@router.get("/blacklisted-ips")
async def list_all_blacklisted_ips():
    client = redis_client.get_client()
    ips = await client.smembers(BLACKLIST_SET_KEY)
    return {"blacklisted_ips": list(ips)}

@router.delete("/unblacklist-ip")   # or @router.post
async def unblacklist_ip(ip: str):
    client = redis_client.get_client()
    await client.srem("demo:blacklisted_ips", ip)
    return {"status": "unblacklisted", "ip": ip}