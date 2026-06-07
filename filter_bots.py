# filter_bots.py
import requests
import pandas as pd
import numpy as np
import json, time

API = "http://localhost:8000/api/v1/debug/inspect"
CSV = "demo_trajectories/bot/generated_fcn_dx_dy_mse_unsupervised.csv"

def row_to_events(row):
    dx = row[:128].values; dy = row[128:256].values
    xs, ys = [0], [0]
    for i in range(len(dx)):
        if dx[i]==0 and dy[i]==0: break
        xs.append(xs[-1]+dx[i]); ys.append(ys[-1]+dy[i])
    if len(xs)<3: return None
    ts = np.arange(len(xs)) * 10  # match training
    return [{"x":int(xs[i]),"y":int(ys[i]),"timestamp":float(ts[i])} for i in range(len(xs))]

bot_df = pd.read_csv(CSV, header=None)
high_conf = []   # indices of bot-like trajectories

for i in range(len(bot_df)):
    ev = row_to_events(bot_df.iloc[i])
    if not ev: continue
    resp = requests.post(API, json={"events": ev})
    if resp.status_code==200:
        data = resp.json()
        if data['probabilities']['bot'] > 0.9:
            high_conf.append(i)
    if (i+1)%50==0: print(f"Processed {i+1}...")

# Save the filtered indices
with open("high_conf_bots.json","w") as f:
    json.dump(high_conf, f)
print(f"✅ {len(high_conf)} high-confidence bot trajectories saved.")