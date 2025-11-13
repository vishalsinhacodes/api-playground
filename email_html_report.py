import os
import ssl
import csv
import smtplib
import mimetypes
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email import encoders
from dotenv import load_dotenv
from datetime import datetime
import pathlib

load_dotenv()
SENDER = os.getenv("MAIL_SENDER")
APP_PASS = os.getenv("MAIL_APP_PASSWORD")
RECEIVER = os.getenv("MAIL_RECEIVER", SENDER)
CURR = os.getenv("CRYPTO_CURRENCY", "inr")

ROOT = pathlib.Path(__file__).parent.resolve()
DATA = ROOT / "data"
CHARTS = ROOT / "charts"

# ---------- readers ----------
def read_repos_latest(path: str, top_n: int = 5):
    rows = []
    p = DATA / path
    if not p.is_file():
        return rows
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            row["stargazers_count"] = int(row.get("stargazers_count") or 0)
            rows.append(row)
    rows.sort(key=lambda r: r["stargazers_count"], reverse=True)
    return rows[:top_n], len(rows), sum(row["stargazers_count"] for row in rows)

def read_weather_latest(path: str):
    p = DATA / path
    if not p.is_file():
        return {}
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            return row
    return {}

def read_crypto_latest(path: str, curr: str):
    p = DATA / path
    if not p.is_file():
        return {}
    prices = []
    latest = None
    with open(p, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            pval = float(row.get(f"price_{curr}") or 0.0)
            prices.append(pval)
            latest = row
    if not prices:
        return {}
    return {
        "latest_iso": latest.get("iso_time"),
        "latest_price": prices[-1],
        "min_price": min(prices),
        "max_price": max(prices),
        "count": len(prices),
    }

# ---------- attachments ----------
def attach_file(msg: MIMEMultipart, filepath: pathlib.Path) -> None:
    if not filepath.is_file():
        return
    ctype, encoding = mimetypes.guess_type(str(filepath))
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with open(filepath, "rb") as f:
        part = MIMEBase(maintype, subtype)
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filepath.name}"')
    msg.attach(part)

def attach_inline_image(msg_root: MIMEMultipart, img_path: pathlib.Path, cid: str) -> None:
    if not img_path.is_file():
        return
    with open(img_path, "rb") as f:
        img = MIMEImage(f.read())
    img.add_header("Content-ID", f"<{cid}>")
    img.add_header("Content-Disposition", "inline", filename=img_path.name)
    msg_root.attach(img)

# ---------- html builder ----------
def build_html(headline, top_repos, totals, weather, crypto, curr: str):
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    style = """
      body{font-family:Arial,Helvetica,sans-serif;margin:0;padding:0;background:#f6f8fb;}
      .wrap{max-width:720px;margin:0 auto;padding:24px;}
      .card{background:#fff;border:1px solid #e6e9ef;border-radius:12px;padding:20px;margin-bottom:16px;}
      h1{font-size:20px;margin:0 0 8px}
      h2{font-size:16px;margin:0 0 12px}
      table{width:100%;border-collapse:collapse;font-size:14px}
      th,td{border-bottom:1px solid #eef1f6;padding:8px;text-align:left;vertical-align:top}
      th{background:#f2f4f8;font-weight:600}
      .muted{color:#667085;font-size:12px}
      .badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#eef6ff}
      .kpi{display:flex;gap:12px;flex-wrap:wrap}
      .kpi .item{background:#fff;border:1px solid #e6e9ef;border-radius:10px;padding:10px 12px}
      .kpi .item b{font-size:16px}
    """
    # Weather
    w_city = weather.get("city") or "-"
    w_country = weather.get("country") or "-"
    w_temp = weather.get("temp") or "-"
    w_desc = weather.get("weather_desc") or weather.get("weather") or "-"
    w_hum = weather.get("humidity_pct") or "-"
    w_wind = weather.get("wind_speed") or "-"

    # Repos table rows
    repo_rows = ""
    for r in top_repos:
        name = r.get("name", "-")
        stars = r.get("stargazers_count", 0)
        url = r.get("html_url", "#")
        lang = r.get("language") or "-"
        repo_rows += f"""
          <tr>
            <td><a href="{url}">{name}</a><br><span class="muted">{lang}</span></td>
            <td>{stars}</td>
            <td><a href="{url}">{url}</a></td>
          </tr>
        """

    html = f"""
    <html>
      <head><meta charset="utf-8"><style>{style}</style></head>
      <body>
        <div class="wrap">
          <div class="card">
            <h1>{headline}</h1>
            <div class="muted">Generated at {today}</div>
            <div class="kpi" style="margin-top:10px">
              <div class="item">Repos: <b>{totals['repos']}</b></div>
              <div class="item">Stars (sum): <b>{totals['stars']}</b></div>
              <div class="item">Crypto Latest: <b>{crypto.get('latest_price','-')} {curr.upper()}</b></div>
              <div class="item">Weather: <b>{w_temp}°</b> <span class="muted">{w_desc}</span></div>
            </div>
          </div>

          <div class="card">
            <h2>🌡️ 7-Day Temp Trend</h2>
            <p class="muted">Recent 7-day temperature snapshot.</p>
            <div style="margin-top:8px">
              <img src="cid:weather_chart" alt="Weather trend" style="max-width:100%;border:1px solid #eee;border-radius:8px"/>
            </div>
          </div>

          <div class="card">
            <h2>₿ Crypto ({curr.upper()})</h2>
            <p class="muted">Inline image below is attached via Content-ID.</p>
            <div style="margin-top:8px">
              <img src="cid:crypto_chart" alt="Crypto chart" style="max-width:100%;border:1px solid #eee;border-radius:8px"/>
            </div>
          </div>

          <div class="card">
            <h2>⭐ Top Repositories</h2>
            <table>
              <thead>
                <tr><th>Repository</th><th>Stars</th><th>Link</th></tr>
              </thead>
              <tbody>
                {repo_rows or '<tr><td colspan="3" class="muted">No repositories found.</td></tr>'}
              </tbody>
            </table>
          </div>

          <div class="muted">CSV attachments included: github_repos_latest.csv, weather_latest.csv, crypto_latest.csv</div>
        </div>
      </body>
    </html>
    """
    return html

def send_html_report() -> None:
    if not SENDER or not APP_PASS:
        raise SystemExit("Missing MAIL_SENDER or MAIL_APP_PASSWORD in .env")

    # Load data from latest snapshots
    top_repos, total_repos, total_stars = read_repos_latest("github_repos_latest.csv", top_n=5)
    weather = read_weather_latest("weather_latest.csv")
    crypto = read_crypto_latest("crypto_latest.csv", curr=CURR)

    totals = {"repos": total_repos, "stars": total_stars}
    headline = "Daily HTML Report: GitHub, Weather & Crypto"

    plain = "Daily report attached: github_repos_latest.csv, weather_latest.csv, crypto_latest.csv\n"
    html = build_html(headline, top_repos, totals, weather, crypto, curr=CURR)

    root = MIMEMultipart("mixed")
    root["Subject"] = headline
    root["From"] = SENDER
    root["To"] = RECEIVER

    body = MIMEMultipart("alternative")
    body.attach(MIMEText(plain, "plain"))
    body.attach(MIMEText(html, "html"))
    root.attach(body)

    # Inline chart
    attach_inline_image(root, CHARTS / "crypto_latest.png", cid="crypto_chart")
    # Inline weather chart
    attach_inline_image(root, CHARTS / "weather_trend_latest.png", cid="weather_chart")

    # Attach the 3 latest CSVs
    for name in ("github_repos_latest.csv", "weather_latest.csv", "crypto_latest.csv"):
        attach_file(root, DATA / name)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER, APP_PASS)
        server.sendmail(SENDER, [RECEIVER], root.as_string())

    print("Sent HTML report with history-backed latest snapshots + inline chart.")

if __name__ == "__main__":
    try:
        send_html_report()
    except Exception as e:
        print(f"Failed to send HTML report: {e}")
