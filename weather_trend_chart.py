"""
weather_trend_chart.py
- Reads dated weather snapshot CSV files from data/
- Picks up to the last 7 snapshots (by snapshot_date or filename)
- Builds a simple temperature vs date chart (PNG)
- Writes dated + rolling latest PNG into charts/
"""

import csv
import pathlib
from datetime import datetime
from typing import List, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
CHARTS_DIR = ROOT / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

def find_weather_files() -> List[pathlib.Path]:
    """
    Find files matching data/weather_*.csv and return them sorted by filename (which contains date).
    This gracefully falls back to weather_latest.csv if no dated files exist.
    """
    files = sorted(DATA_DIR.glob("weather_*_*.csv")) # e.g., weather_Delhi_IN_20251111.csv
    # Exclude the rolling latest if it exists in same pattern
    dated = [p for p in files if "latest" not in p.name.lower()]    
    if dated:
        return dated
    # fallback to latest only
    latest = DATA_DIR / "weather_latest.csv"
    return [latest] if latest.exists() else []

def read_temp_from_csv(path: pathlib.Path) -> Tuple[str, float]:
    """
    Read a one-row weather CSV snapshot and return (label, temp).
    Label will be snapshot_date or iso timestamp.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # try snapshot_date, then iso/time fields, then filename date
            label = row.get("snapshot_date") or row.get("iso_time") or path.stem 
            # prefer numeric fields in order: temp, main temp fields
            temp = row.get("temp") or row.get("temp_max") or row.get("temp_min")   
            try:
                temp_val = float(temp) if temp is not None and temp != "" else None
            except Exception:
                temp_val = None
            return(label, temp_val)
        return(path.stem, None)
    
def collect_last_n_temperatures(n: int = 7) -> List[Tuple[str, float]]:
    files = find_weather_files()
    if not files:
        raise SystemExit("No weather files found in data/. Run weather_current_to_csv.py first.")    
    # pick the last n files by sorted order (which is by name/date)
    recent = files[-n:]
    data = []
    for p in recent:
        label, temp = read_temp_from_csv(p)
        # ensure label is friendly: if YYYYMMDD convert to YYYY-MM-DD
        try:
            if len(label) == 8 and label.isdigit():
                label = datetime.strptime(label, "%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            pass
        data.append((label, temp))
        
    # Filter out entries where temp is None, but keep ordering
    filtered = [(lbl, t) for (lbl, t) in data if t is not None]
    if not filtered:
        raise SystemExit("Found weather files but none had numeric temperature values.")
    return filtered

def build_and_save_chart(points: List[Tuple[str, float]]) -> None:
    # x labels and y values
    x_labels = [p[0] for p in points]
    y_values = [p[1] for p in points]
    
    # Plot
    plt.figure(figsize=(8, 3))
    plt.plot(x_labels, y_values, marker="o", linewidth=2)
    plt.title("Temperature trend (last {} days)".format(len(points)))
    plt.xlabel("Date")
    plt.ylabel("Temperature (°C)")
    plt.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)
    plt.tight_layout()
    
    # filenames
    today = datetime.now().strftime("%Y%m%d")
    png_name = f"weather_trend_{today}.png"
    png_path = CHARTS_DIR / png_name
    png_latest = CHARTS_DIR / "weather_trend_latest.png"
    
    # Save both dated and latest
    plt.savefig(png_path, dpi=120)
    plt.savefig(png_latest, dpi=120)
    plt.close()
    
    print(f"✅ Saved weather trend chart: {png_path.name} and weather_trend_latest.png")
    
if __name__ == "__main__":
    points = collect_last_n_temperatures(7)
    build_and_save_chart(points)    