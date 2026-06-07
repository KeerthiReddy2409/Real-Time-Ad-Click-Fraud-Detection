import json, glob, random, os, warnings
import pandas as pd
import numpy as np
from fastapi import APIRouter
from app.models.request import MouseEvent
from app.services.layer1_bouncer import Layer1Bouncer
from app.services.layer2_detective import detective
from app.core.redis_client import redis_client

warnings.filterwarnings("ignore")

router = APIRouter(prefix="/demo", tags=["demo"])

# ---------- Paths ----------
HUMAN_DIR = "/app/demo_trajectories/human/*.json"
BOT_CSV   = "/app/demo_trajectories/bot/generated_fcn_dx_dy_mse_unsupervised.csv"
HIGH_CONF = "/app/high_conf_bots.json"

current_rate_limit = 5   # default

# ---------- Random IP generator (documentation subnets) ----------
DOC_SUBNETS = [
    (192, 0, 2, 0),
    (198, 51, 100, 0),
    (203, 0, 113, 0),
]

VPN_IPS = [
    "102.130.113.9",      # ProtonVPN
    "45.133.172.1",
    "185.220.101.1",
    "104.223.91.1",
    "198.44.187.1"
]
def is_vpn(ip): return ip in VPN_IPS

# def random_demo_ip():
#     if random.random() < 0.3:   # 30% chance of using a VPN IP
#         return random.choice(list(VPN_IPS))
#     base = random.choice(DOC_SUBNETS)
#     return f"{base[0]}.{base[1]}.{base[2]}.{random.randint(1, 254)}"

def random_demo_ip():
    """Return a random IP that is NOT currently blacklisted."""
    # Try up to 20 times to find a clean IP
    for _ in range(20):
        ip = _random_ip()
        if not redis_client.is_ip_blacklisted(ip):
            return ip
    # Fallback: return any fresh IP (extremely unlikely to be blacklisted)
    return _random_ip()

def _random_ip():
    if random.random() < 0.3:   # 30% chance of using a VPN IP
        return random.choice(list(VPN_IPS))
    base = random.choice(DOC_SUBNETS)
    return f"{base[0]}.{base[1]}.{base[2]}.{random.randint(1, 254)}"

# ---------- Dynamic IP sets ----------
_bot_ips = set()                # IPs flagged as bots (for the summary)
BLACKLIST_SET_KEY = "demo:blacklisted_ips"

# ---------- Lazy caches ----------
_human_cache = None
_bot_events_cache = None
_high_conf_indices = None

def load_human():
    global _human_cache
    if _human_cache is None:
        _human_cache = []
        for f in glob.glob(HUMAN_DIR):
            try:
                with open(f) as fp:
                    traj = json.load(fp)
                    if isinstance(traj, list) and len(traj) > 2:
                        _human_cache.append(traj)
            except Exception:
                pass
        print(f"Lazy-loaded {len(_human_cache)} human trajectories")
    return _human_cache

def _row_to_events(row):
    dx = row[:128].values
    dy = row[128:256].values
    xs, ys = [0], [0]
    for k in range(len(dx)):
        if dx[k] == 0 and dy[k] == 0:
            break
        xs.append(xs[-1] + dx[k])
        ys.append(ys[-1] + dy[k])
    if len(xs) < 3:
        return None
    ts = [i * 10.0 for i in range(len(xs))]
    return [{"x": int(xs[i]), "y": int(ys[i]), "timestamp": float(ts[i])} for i in range(len(xs))]

def load_bot_data():
    global _bot_events_cache, _high_conf_indices
    if _bot_events_cache is None:
        if not os.path.exists(BOT_CSV):
            print(f"Bot CSV not found at {BOT_CSV}")
            _bot_events_cache = []
            _high_conf_indices = []
            return

        if os.path.exists(HIGH_CONF):
            with open(HIGH_CONF) as f:
                _high_conf_indices = json.load(f)
            print(f"Loaded {len(_high_conf_indices)} high‑conf indices")
        else:
            _high_conf_indices = []

        max_idx = max(_high_conf_indices) if _high_conf_indices else 499
        rows_to_load = max_idx + 1

        bot_df = pd.read_csv(BOT_CSV, header=None)
        actual_rows = min(rows_to_load, len(bot_df))
        _bot_events_cache = [None] * actual_rows
        print(f"Loading {actual_rows} bot trajectories…")
        for i in range(actual_rows):
            ev = _row_to_events(bot_df.iloc[i])
            _bot_events_cache[i] = ev
        print(f"Bot trajectories loaded (up to row {actual_rows-1})")

def get_guaranteed_bot():
    load_bot_data()
    if _high_conf_indices and _bot_events_cache:
        # Randomly pick a verified bot index – all are guaranteed
        idx = random.choice(_high_conf_indices)
        if idx < len(_bot_events_cache) and _bot_events_cache[idx] is not None:
            return _bot_events_cache[idx]
    # Fallback to any available bot
    if _bot_events_cache:
        for ev in _bot_events_cache:
            if ev is not None:
                return ev
    return None

def random_human():
    trajs = load_human()
    return random.choice(trajs) if trajs else None

# In demo.py, locate run_verification and replace it with:

async def run_verification(demo_ip: str, device: str, events: list,
                           collect_bot_ip: bool = True):
    # Convert dicts to MouseEvent objects
    mouse_events = [MouseEvent(**e) for e in events]
    
    allowed, reason = await Layer1Bouncer.analyze(demo_ip, device)
    if not allowed:
        verdict, confidence, layer, risk = "bot", 0.99, 1, 0.9
    else:
        ml = await detective.analyze(mouse_events)
        verdict = ml["verdict"]
        confidence = ml["confidence"]
        layer = 2
        risk = ml["risk_score"]
        reason = ml.get("reason", "ML analysis")

    # ---- Session caching ----
    session_id = f"demo_{random.randint(0,99999)}"
    
    # Publish the main verification event
    try:
        client = redis_client.get_client()
        msg = json.dumps({
            "session_id": session_id,
            "ip": demo_ip,
            "verdict": verdict,
            "confidence": confidence,
            "layer_triggered": layer,
            "reason": reason,
            "risk_score": risk,
            "device_fingerprint": device,
            "mouse_events_count": len(events),
            "vpn": is_vpn(demo_ip)
        })
        await client.publish("clickguard:decisions", msg)
    except Exception as e:
        print(f"Redis publish error: {e}")

    # Cache session for forensic view
    try:
        await client.hset(f"session:{session_id}", mapping={
            "demo_ip": demo_ip,
            "device": device,
            "verdict": verdict,
            "confidence": confidence,
            "layer": layer,
            "reason": reason,
            "risk_score": risk,
            "events_json": json.dumps(events),
            "vpn": str(is_vpn(demo_ip))
        })
        # Expire after 10 minutes (enough for demo)
        await client.expire(f"session:{session_id}", 600)
    except Exception as e:
        print(f"Redis cache error: {e}")

    # Automatic blacklist (unchanged)
    blacklisted = False
    if collect_bot_ip and verdict == "bot" and demo_ip not in _bot_ips:
        _bot_ips.add(demo_ip)
        await redis_client.add_to_blacklist(demo_ip)
        client = redis_client.get_client()
        await client.sadd(BLACKLIST_SET_KEY, demo_ip)
        blacklisted = True

    return {"verdict": verdict, "confidence": confidence, "layer": layer, "reason": reason, "blacklisted": blacklisted}
# ---------- Endpoints ----------
# @router.post("/human")
# async def demo_human():
#     events = random_human()
#     if not events:
#         return {"error": "no human trajectories"}
#     ip = random_demo_ip()
#     device = f"dev_human_{ip.split('.')[-1]}"

#     mouse_events = [MouseEvent(**e) for e in events]
#     ml = await detective.analyze(mouse_events)
#     verdict = ml["verdict"]
#     confidence = ml["confidence"]
#     risk = ml["risk_score"]
#     reason = ml.get("reason", "ML analysis")

#     # ---- Generate one session ID and use it everywhere ----
#     session_id = f"human_{random.randint(0,99999)}"

#     # Publish to dashboard
#     try:
#         client = redis_client.get_client()
#         msg = json.dumps({
#             "session_id": session_id,   # <-- same ID
#             "ip": ip,
#             "verdict": verdict,
#             "confidence": confidence,
#             "layer_triggered": 2,
#             "reason": reason,
#             "risk_score": risk,
#             "device_fingerprint": device,
#             "mouse_events_count": len(events),
#             "vpn": is_vpn(ip),
#             "blacklisted": False
#         })
#         await client.publish("clickguard:decisions", msg)
#     except Exception as e:
#         print(f"Redis publish error: {e}")

#     # Cache session for forensic view (using the same session_id)
#     try:
#         await client.hset(f"session:{session_id}", mapping={
#             "demo_ip": ip,
#             "device": device,
#             "verdict": verdict,
#             "confidence": confidence,
#             "layer": 2,
#             "reason": reason,
#             "risk_score": risk,
#             "events_json": json.dumps(events),
#             "vpn": str(is_vpn(ip))
#         })
#         await client.expire(f"session:{session_id}", 600)
#     except Exception as e:
#         print(f"Redis cache error: {e}")

#     return {"verdict": verdict, "confidence": confidence, "layer": 2, "reason": reason}

@router.post("/human")
async def demo_human():
    events = random_human()
    if not events:
        return {"error": "no human trajectories"}
    ip = random_demo_ip()
    device = f"dev_human_{ip.split('.')[-1]}"
    return await run_verification(ip, device, events)

@router.post("/bot")
async def demo_bot():
    events = get_guaranteed_bot()
    if not events:
        return {"error": "no bot trajectories"}
    ip = random_demo_ip()
    return await run_verification(ip, f"dev_bot_{ip.split('.')[-1]}", events)

@router.post("/ratelimit")
async def demo_rate_limit():
    ip = random_demo_ip()
    device = f"dev_rl_{ip.split('.')[-1]}"
    results = []
    for i in range(35):
        events = random_human()
        if not events:
            continue
        res = await run_verification(ip, device, events, collect_bot_ip=True)
        results.append(res)
    return {"count": len(results)}

@router.get("/blacklisted-ips")
async def list_blacklisted_ips():
    """Return all IPs that have been flagged as bots in this demo session."""
    return {"bot_ips": list(_bot_ips)}

@router.delete("/clear-bot-ips")
async def clear_bot_ips():
    """Reset the collected bot IPs (useful after a demo)."""
    _bot_ips.clear()
    client = redis_client.get_client()
    await client.delete(BLACKLIST_SET_KEY)
    return {"status": "cleared"}

@router.post("/mix")
async def demo_mix():
    action_list = []
    for _ in range(random.randint(2, 4)):
        action_list.append("human")
    for _ in range(random.randint(2, 4)):
        action_list.append("bot")
    for _ in range(random.randint(1, 2)):
        action_list.append("ratelimit")
    if random.random() < 0.5:
        action_list.append("vpnbot")
    random.shuffle(action_list)

    results = []
    for action in action_list:
        if action == "human":
            await demo_human()
            results.append("human")
        elif action == "bot":
            await demo_bot()
            results.append("bot")
        elif action == "ratelimit":
            await demo_rate_limit()
            results.append("ratelimit")

    blacklist_resp = await list_blacklisted_ips()
    results.append(f"blacklist ({blacklist_resp.get('bot_ips', [])})")
    return {"actions": results}

@router.post("/set-rate-limit")
async def set_rate_limit(limit: int = 5):
    global current_rate_limit
    if limit < 1:
        limit = 1
    current_rate_limit = limit
    return {"rate_limit_max": limit}

@router.get("/rate-limit")
async def get_rate_limit():
    return {"rate_limit_max": current_rate_limit}