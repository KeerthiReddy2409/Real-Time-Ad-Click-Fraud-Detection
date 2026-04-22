from typing import Tuple, Optional
from app.core.redis_client import redis_client
class Layer1Bouncer:
    RATE_LIMIT_MAX = 5
    DEVICE_WINDOW = 300
    DEVICE_THRESHOLD = 50
    
    @classmethod
    async def analyze(cls, ip: str, device_fingerprint: str) -> Tuple[bool, Optional[str]]:
        client = redis_client.get_client()
        if not client:
            return True, None
        
        print(f"🔍 Analyzing IP: {ip}, Device: {device_fingerprint[:20]}...")
        
        # 1. IP Blacklist
        if await redis_client.is_ip_blacklisted(ip):
            print(f"❌ IP blacklisted: {ip}")
            return False, "IP blacklisted"
        
        # 2. Rate Limiting
        allowed = await redis_client.check_rate_limit(ip, max_requests=cls.RATE_LIMIT_MAX)
        if not allowed:
            print(f"❌ Rate limit exceeded for IP: {ip}")
            return False, "Rate limit exceeded"
        print(f"✅ Rate limit OK for IP: {ip}")
        
        # 3. Device Anomaly
        device_count = await redis_client.track_device_request(device_fingerprint, window_sec=cls.DEVICE_WINDOW)
        print(f"📱 Device request count: {device_count}")
        if device_count > cls.DEVICE_THRESHOLD:
            print(f"❌ Device anomaly: {device_fingerprint}")
            return False, f"Device anomaly: {device_count} requests in {cls.DEVICE_WINDOW}s"
        
        return True, None