# demo_simulator.py
import requests
import json
import glob
import random
import time
import numpy as np
import pandas as pd

API = "http://localhost:8000/api/v1/verify"
# ---- CONFIGURATION ----
HUMAN_DIR = "demo_trajectories/human/*.json"
BOT_CSV   = "demo_trajectories/bot/generated_fcn_dx_dy_mse_unsupervised.csv"   # adjust if needed
USE_CURSORY = False   # set to True after pip install cursory

# ---- Load human trajectories ----
human_trajs = []
for f in glob.glob(HUMAN_DIR):
    with open(f) as fp:
        traj = json.load(fp)
        if isinstance(traj, list) and len(traj) > 2:
            human_trajs.append(traj)
print(f"✅ Loaded {len(human_trajs)} human trajectories")

# ---- Load autoencoder bot trajectories ----
def deltas_to_events(row):
    dx = row[:128].values
    dy = row[128:256].values
    xs, ys = [0], [0]
    for i in range(len(dx)):
        if dx[i] == 0 and dy[i] == 0:
            break
        xs.append(xs[-1] + dx[i])
        ys.append(ys[-1] + dy[i])
    if len(xs) < 3:
        return None
    time_deltas = np.random.lognormal(mean=2.5, sigma=0.4, size=len(xs)-1)
    time_deltas = np.clip(time_deltas, 2, 50)
    ts = np.concatenate([[0], np.cumsum(time_deltas)])
    return [{"x": int(xs[i]), "y": int(ys[i]), "timestamp": float(ts[i])} for i in range(len(xs))]

try:
    bot_csv_df = pd.read_csv(BOT_CSV, header=None)
    autoencoder_bots = []
    for i in range(min(500, len(bot_csv_df))):
        ev = deltas_to_events(bot_csv_df.iloc[i])
        if ev:
            autoencoder_bots.append(ev)
    print(f"✅ Loaded {len(autoencoder_bots)} autoencoder bot trajectories")
except FileNotFoundError:
    print("⚠️ Autoencoder CSV not found – skipping high‑realism bots")
    autoencoder_bots = []

try:
    with open("high_conf_bots.json", "r") as f:
        high_conf_indices = json.load(f)
    # Keep only indices that exist in our loaded autoencoder_bots list
    max_idx = len(autoencoder_bots)
    high_conf_indices = [i for i in high_conf_indices if i < max_idx]
    print(f"✅ Loaded {len(high_conf_indices)} high‑confidence bot indices (filtered to first {max_idx} bots)")
except FileNotFoundError:
    print("⚠️ high_conf_bots.json not found. Run filter_bots.py first.")
    high_conf_indices = []


# ---- Straight‑line bot (backup for obvious bot demo) ----
# STRAIGHT_BOT = [
#     {"x":100,"y":100,"timestamp":0},{"x":140,"y":140,"timestamp":20},
#     {"x":180,"y":180,"timestamp":40},{"x":220,"y":220,"timestamp":60},
#     {"x":260,"y":260,"timestamp":80},{"x":300,"y":300,"timestamp":100},
#     {"x":340,"y":340,"timestamp":120},{"x":380,"y":380,"timestamp":140},
#     {"x":420,"y":420,"timestamp":160},{"x":460,"y":460,"timestamp":180},
#     {"x":500,"y":500,"timestamp":200}
# ]

# ---- Demo IPs and devices ----
IPS = ["192.168.1.10", "203.0.113.5", "10.0.0.55", "198.51.100.22", "203.0.113.99"]
DEVICES = [f"dev_{i:03d}" for i in range(1, 6)]

def send_request(demo_ip, device, events, desc=""):
    headers = {"X-Demo-IP": demo_ip}
    payload = {
        "session_id": f"sim_{random.randint(0,99999)}",
        "device_fingerprint": device,
        "user_agent": "Mozilla/5.0 (Demo)",
        "mouse_events": events,
        "click_timestamp": events[-1]["timestamp"] + 10,
        "page_url": "http://localhost:3000"
    }
    resp = requests.post(API, json=payload, headers=headers).json()
    print(f"[{desc}] IP {demo_ip} → {resp['verdict']} (L{resp['layer_triggered']})")
    return resp

def get_high_conf_bot():
    if not high_conf_indices or autoencoder_bots is None:
        return random.choice(autoencoder_bots) if autoencoder_bots else None
    idx = random.choice(high_conf_indices)
    return autoencoder_bots[idx]   # autoencoder_bots is already a list of event dicts

# =================== DEMO SCENARIOS ===================
def demo():
    # 1. Legitimate human
    if human_trajs:
        print("\n👤 Legitimate human user...")
        send_request("192.168.1.10", "dev_001", random.choice(human_trajs), "Legit")
        time.sleep(1)

    # 2. Obvious bot (autoencoder bot)
    if autoencoder_bots:
        print("\n🤖 Obvious bot (autoencoder generated)...")
        send_request("203.0.113.5", "dev_002", get_high_conf_bot(), "ObviousBot")
        time.sleep(1)

    # 3. Sneaky bot (another autoencoder bot)
    if len(autoencoder_bots) > 1:
        print("\n🕵️ Sneaky bot (different autoencoder sample)...")
        send_request("198.51.100.22", "dev_003", get_high_conf_bot(), "SneakyBot")
        time.sleep(1)

    # 4. Cursory‑generated bot (only if enabled)
    if USE_CURSORY:
        try:
            from cursory import generate_trajectory
            def cursory_bot():
                points, timings = generate_trajectory(target_start=(100,100), target_end=(700,500))
                ts = np.cumsum(timings)
                ts = np.insert(ts, 0, 0)
                return [{"x":int(p[0]),"y":int(p[1]),"timestamp":float(ts[i])} for i,p in enumerate(points)]
            print("\n🌀 Advanced bot (cursory generated)...")
            send_request("192.0.2.33", "dev_004", cursory_bot(), "CursoryBot")
            time.sleep(1)
        except ImportError:
            print("⚠️ cursory not installed – skipping")

    # 5. Rate limit attack (using human trajectories rapidly)
    if human_trajs:
        print("\n🔥 Rate limit attack from 10.0.0.55...")
        for i in range(35):
            send_request("10.0.0.55", "dev_005", random.choice(human_trajs), f"RateLimit_{i+1}")
            time.sleep(0.05)

    # 6. Blacklisted IP (pre‑blacklist via admin endpoint)
    requests.post("http://localhost:8000/api/v1/admin/blacklist-ip?ip=203.0.113.99")
    print("\n⚠️ Blacklisted IP 203.0.113.99...")
    send_request("203.0.113.99", "dev_999", random.choice(human_trajs) if human_trajs else STRAIGHT_BOT, "Blacklist")

    print("\n✅ Demo complete.")

if __name__ == "__main__":
    demo()