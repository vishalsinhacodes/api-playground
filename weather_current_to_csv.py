import os
import csv
import pathlib
import requests
from datetime import datetime
from typing import Dict,Any
from dotenv import load_dotenv

# 1) Load config from .env
load_dotenv()
API_KEY = os.getenv("OWN_API_KEY")
CITY = os.getenv("OWN_CITY", "Noida")
COUNTRY = os.getenv("OWN_COUNTRY","IN")
UNITS = os.getenv("OWN_UNITS", "metric") # metric = °C, imperial = °F

# 2) Basic guardrail: ensure key exists
if not API_KEY:
    raise SystemError("Missing OWN_API_KEY in .env")

ROOT = pathlib.Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 3) Build endpoint and params
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
params = {
    "q": f"{CITY},{COUNTRY}",
    "appid": API_KEY,
    "units": UNITS
}

# 4) Make the HTTP GET request
resp = requests.get(BASE_URL, params=params, timeout=20)

# 5) Validate status
if resp.status_code == 401:
    raise SystemExit("[401] Invalid API key. Re-check OWN_API_KEY in .env")

if resp.status_code == 404:
    raise SystemExit(f"[404] City not found: {CITY},{COUNTRY}")

if resp.status_code != 200:
    raise SystemExit(f"[{resp.status_code}] Unexpected error: {resp.text}")

# 6) Parse JSON -> Pthon dict
data: Dict[str, Any] = resp.json()

# 7) Extract useful fields safely
def g(path, default=None):
    """
    Tiny helper to safely read nested fields from the JSON dict.
    Usage: g(['main','temp']) → data['main']['temp'] if exists, else default.
    """
    
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

row = {
    "snapshot_date": datetime.now().strftime("%Y-%m-%d"),
    "city": g(["name"]),
    "country": g(["sys", "country"]),
    "weather": g(["weather"], [{}])[0].get("main") if g(["weather"]) else None,
    "weather_desc": g(["weather"], [{}])[0].get("description") if g(["weather"]) else None,
    "temp": g(["main", "temp"]),
    "feels_like": g(["main", "feels_like"]),
    "temp_min": g(["main", "temp_min"]),
    "temp_max": g(["main", "temp_max"]),
    "pressure_hpa": g(["main", "pressure"]),
    "humidity_pct": g(["main", "humidity"]),
    "wind_speed": g(["wind", "speed"]),
    "wind_deg": g(["wind", "deg"]),
    "clouds_pct": g(["clouds", "all"]),
    "visibility_m": g(["visibility"]),
    "timestamp": g(["dt"]),  # Unix epoch seconds
}

today = datetime.now().strftime("%Y%m%d")
dated = DATA_DIR / f"weather_{CITY}_{COUNTRY}_{today}.csv"
latest = DATA_DIR / "weather_latest.csv"

# 8) Save single-row CSVs (dated + latest)
for path in (dated, latest):
    with open (path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    
print(f"✅ Saved Weather snapshots: {dated.name} & weather_latest.csv for {row['city']}, {row['country']}")
