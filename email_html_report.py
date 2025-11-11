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

# 1) Load .env
load_dotenv()
SENDER = os.getenv("MAIL_SENDER")
APP_PASS = os.getenv("MAIL_APP_PASSWORD")
RECEIVER = os.getenv("MAIL_RECEIVER", SENDER)

# ---------- data readers ----------

def read_top_repos(csv_path: str, top_n: int = 5):
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            row["stargazers_count"] = int(row.get("stargazers_count") or 0)
            rows.append(row)
    rows.sort(key=lambda r: r["stargazers_count"], reverse=True)
    return rows[:top_n]

def read_weather(csv_path: str):
    if not os.path.isfile(csv_path):
        return {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            return row
    return {}

def read_crypto_latest(csv_path: str, curr: str):
    """Return summary dict: latest price, min, max, count."""
    if not os.path.isfile(csv_path):
        return {}
    prices = []
    latest = None
    with open(csv_path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            p = float(row.get(f"price_{curr}") or 0.0)
            prices.append(p)
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

# ---------- attachments & html ----------

def attach_file(msg: MIMEMultipart, filepath: str) -> None:
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Attachment not found: {filepath}")
    ctype, encoding = mimetypes.guess_type(filepath)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with open(filepath, "rb") as f:
        part = MIMEBase(maintype, subtype)
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(filepath)}"')
    msg.attach(part)

def attach_inline_image(msg_root: MIMEMultipart, img_path: str, cid: str) -> None:
    """Attach image as inline (Content-ID). Reference with <img src="cid:..."> in HTML."""
    if not os.path.isfile(img_path):
        return
    with open(img_path, "rb") as f:
        img = MIMEImage(f.read())
    img.add_header("Content-ID", f"<{cid}>")
    img.add_header("Content-Disposition", "inline", filename=os.path.basename(img_path))
    msg_root.attach(img)

def build_html(top_repos, weather, crypto, curr: str):
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
    """

    # Weather bits
    w_city = weather.get("city") or "-"
    w_country = weather.get("country") or "-"
    w_temp = weather.get("temp") or "-"
    w_desc = weather.get("weather_desc") or weather.get("weather") or "-"
    w_hum = weather.get("humidity_pct") or "-"
    w_wind = weather.get("wind_speed") or "-"

    # Crypto bits
    latest = crypto.get("latest_price")
    c_min = crypto.get("min_price")
    c_max = crypto.get("max_price")
    c_time = crypto.get("latest_iso")
    crypto_block = f"""
      <p style="margin:8px 0 0;">
        Latest: <strong>{latest if latest is not None else '-'}</strong> {curr.upper()}<br>
        Range (last {crypto.get('count','-')} pts): {c_min} – {c_max} {curr.upper()}<br>
        Updated: {c_time or '-'}
      </p>
      <div style="margin-top:8px">
        <img src="cid:crypto_chart" alt="Crypto chart" style="max-width:100%;border:1px solid #eee;border-radius:8px"/>
      </div>
    """

    # Repos rows
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
            <h1>Daily Automation Report</h1>
            <div class="muted">Generated at {today}</div>
          </div>

          <div class="card">
            <h2>🌤️ Weather</h2>
            <div><span class="badge">{w_city}, {w_country}</span></div>
            <p style="margin:8px 0 0;">{w_desc} — <strong>{w_temp}°</strong> (humidity {w_hum}%, wind {w_wind})</p>
          </div>

          <div class="card">
            <h2>₿ Crypto ({curr.upper()})</h2>
            {crypto_block}
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

          <div class="muted">CSV attachments included: repos.csv, weather.csv, crypto_latest.csv</div>
        </div>
      </body>
    </html>
    """
    return html

def send_html_report(attachments: list[str], curr: str) -> None:
    if not SENDER or not APP_PASS:
        raise SystemExit("Missing MAIL_SENDER or MAIL_APP_PASSWORD in .env")

    # Load data
    top_repos = read_top_repos("repos.csv", top_n=5)
    weather = read_weather("weather.csv")
    crypto = read_crypto_latest("data/crypto_latest.csv", curr=curr)

    # Body parts
    plain = "Daily report attached.\n- repos.csv\n- weather.csv\n- crypto_latest.csv\n"
    html = build_html(top_repos, weather, crypto, curr)

    # Root with attachments
    root = MIMEMultipart("mixed")
    root["Subject"] = "Daily HTML Report: GitHub, Weather & Crypto"
    root["From"] = SENDER
    root["To"] = RECEIVER

    # Body (plain + html)
    body = MIMEMultipart("alternative")
    body.attach(MIMEText(plain, "plain"))
    body.attach(MIMEText(html, "html"))
    root.attach(body)

    # Inline crypto chart
    attach_inline_image(root, "charts/crypto_latest.png", cid="crypto_chart")

    # File attachments
    for path in attachments:
        attach_file(root, path)

    # Send
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER, APP_PASS)
        server.sendmail(SENDER, [RECEIVER], root.as_string())

    print("✅ Sent HTML report with inline chart and attachments.")

if __name__ == "__main__":
    try:
        curr = os.getenv("CRYPTO_CURRENCY", "inr")
        send_html_report(["repos.csv", "weather.csv", "data/crypto_latest.csv"], curr=curr)
    except Exception as e:
        print(f"❌ Failed to send HTML report: {e}")
