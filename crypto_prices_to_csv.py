import os
import csv
import time
from datetime import datetime
import requests
import pathlib
from typing import List, Dict, Any
from dotenv import load_dotenv

# Charting
import matplotlib
matplotlib.use("Agg") # render without a GUI
import matplotlib.pyplot as plt

# 1) Load config
load_dotenv()
COIN = os.getenv("CRYPTO_COIN", "bitcoin")
CURR = os.getenv("CRYPTO_CURRENCY", "inr")
DAYS = os.getenv("CRYPTO_DAYS", "7")

ROOT = pathlib.Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
CHARTS_DIR = ROOT / "charts"
DATA_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)

# 2) Build CoinGecko endpoint (public, no key)
#    Example: https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=inr&days=7
BASE = "https://api.coingecko.com/api/v3/coins"
URL = f"{BASE}/{COIN}/market_chart"
params = {"vs_currency": CURR, "days": DAYS}

# 3) Call the API with basic headers + timeout
resp = requests.get(URL, params=params, headers={"Accept": "application/json", "User-Agent": "api-playground"}, timeout=30)

if resp.status_code != 200:
    raise SystemExit(f"[{resp.status_code}] CoinGecko error: {resp.text[:300]}")

payload: Dict[str, Any] = resp.json()

# 4) The 'prices' array -> list of [timestamp_ms, price]
raw_prices = payload.get("prices", [])
if not raw_prices:
    raise SystemExit("No 'prices' in CoinGecko response.")

# 5) Transform to rows from csv (ISO time + numeric price)
rows: List[Dict[str, Any]] = []
for ts_ms, price in raw_prices:
    # convert ms -> seconds, then to ISO local time for readability
    ts = int(ts_ms) // 1000
    iso = datetime.fromtimestamp(ts).isoformat(timespec="seconds")
    rows.append({"timestamp": ts, "iso_time": iso, f"price_{CURR}": float(price)})
    
# 6) Decide filenames (dated + latest)
today = datetime.now().strftime("%Y%m%d")
csv_name = f"crypto_{COIN}_{CURR}_{today}.csv"
png_name = f"crypto_{COIN}_{CURR}_{today}.png"

csv_path = DATA_DIR / csv_name
csv_latest = DATA_DIR / "crypto_latest.csv"
png_path = CHARTS_DIR / png_name
png_latest = CHARTS_DIR / "crypto_latest.png"

# 7) Save csv (dated snapshot)
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    
# Also overwrite a rolling 'latest' file (useful for the email)
with open(csv_latest, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    
# 8) Build the chart (time on X, price on Y)
#    Keep it clean and readable; no seaborn.
x = [datetime.fromtimestamp(r["timestamp"]) for r in rows]
y = [r[f"price_{CURR}"] for r in rows]

plt.figure(figsize=(8,3))
plt.plot(x, y, linewidth=2)
plt.title(f"{COIN.capitalize()} price ({CURR.upper()}) - last {DAYS} day(s)")
plt.xlabel("Time")
plt.ylabel(f"Price ({CURR.upper()})")
plt.tight_layout()
plt.savefig(png_path, dpi=120)
plt.savefig(png_latest, dpi=120)
plt.close()

print(f"Saved: {csv_path.name} and chart {png_path.name}")
