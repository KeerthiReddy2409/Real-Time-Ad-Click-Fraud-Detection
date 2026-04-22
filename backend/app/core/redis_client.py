import asyncio
import redis.asyncio as redis
from app.core.config import settings
from typing import Optional

class RedisClient:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Establish connection to Redis and initialize Bloom filter."""
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Small delay to let Redis fully initialize
        await asyncio.sleep(1)
        await self.client.ping()
        print("✅ Connected to Redis")
        
        # Initialize Bloom filter for IP blacklist
        try:
            await self.client.execute_command("BF.RESERVE", "ip_blacklist", 0.01, 10000)
        except Exception as e:
            # Filter may already exist - that's fine
            print(f"Bloom filter init note: {e}")
        print("✅ RedisBloom filter ready")
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            print("❌ Disconnected from Redis")
    
    def get_client(self):
        """Return the Redis client instance."""
        return self.client

    # ---------- IP Blacklist (Bloom Filter) ----------
    async def is_ip_blacklisted(self, ip: str) -> bool:
        """Check if IP exists in Bloom filter."""
        return await self.client.execute_command("BF.EXISTS", "ip_blacklist", ip) == 1
    
    async def add_to_blacklist(self, ip: str):
        """Add IP to Bloom filter."""
        await self.client.execute_command("BF.ADD", "ip_blacklist", ip)
    
    # ---------- Sliding Window Rate Limiter ----------
    async def check_rate_limit(self, ip: str, max_requests: int = 30, window_sec: int = 60) -> bool:
        """
        Returns True if under limit, False if rate exceeded.
        Uses Redis sorted set with sliding window.
        """
        key = f"rate_limit:{ip}"
        time_result = await self.client.time()
        now = time_result[0]  # Unix timestamp as integer
        
        # Remove old entries
        await self.client.zremrangebyscore(key, 0, now - window_sec)
        
        # Count current window
        count = await self.client.zcard(key)
        if count >= max_requests:
            return False
        
        # Add current request
        await self.client.zadd(key, {str(now): now})
        await self.client.expire(key, window_sec + 10)
        return True
    
    # ---------- Device Fingerprint Tracker ----------
    async def track_device_request(self, device_id: str, window_sec: int = 300) -> int:
        """
        Track request count for a device fingerprint in last window_sec.
        Returns the new count.
        """
        key = f"device:{device_id}"
        time_result = await self.client.time()
        now = time_result[0]
        
        # Remove old entries
        await self.client.zremrangebyscore(key, 0, now - window_sec)
        
        # Add current request with unique member
        import random
        member = f"{now}:{random.randint(1000,9999)}"
        await self.client.zadd(key, {member: now})
        await self.client.expire(key, window_sec + 10)
        
        count = await self.client.zcard(key)
        return count

redis_client = RedisClient()