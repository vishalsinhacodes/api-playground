import os
import csv
import ssl
import smtplib
import mimetypes
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
from dotenv import load_dotenv
from datetime import datetime

# 1) Load .env (keeps secrets & config out of code)
load_dotenv()
SENDER = os.getenv("MAIL_SENDER")
APP_PASS = os.getenv("MAIL_APP_PASSWORD")
RECEIVER = os.getenv("MAIL_RECEIVER", SENDER)

# ---------- helpers: data loading ----------

def read_top_repos(csv_path: str, top_n: int = 5):
    """Read repos.csv and return top repos by stars (desc)."""
    rows = []
    if not os.path.isfile(csv_path):
        return rows
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # safe conversions
            r["stargazers_count"] = int(r.get("stargazers_count") or 0)
            rows.append(r)
    rows.sort(key=lambda r: r["stargazers_count"], reverse=True)
    return rows[:top_n]

def read_weather(csv_path: str):
    """Read single-row weather.csv snapshot."""
    if not os.path.isfile(csv_path):
        return{}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            return r # first row only
    return {}

# ---------- helpers: email building ----------
def attach_file(msg: MIMEMultipart, filepath: str) -> None:
    """Attach arbitrary file with correct MIME type."""    
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
    
def build_html(top_repos, weather):
    """Return a clean HTML string fro the inline report."""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # minimal, safe inline-styles for wide client support
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
    
    # weather block
    w_city = weather.get("city") or "-"
    w_country = weather.get("country") or "-"
    w_temp = weather.get("temp") or "-"
    w_desc = weather.get("weather_desc") or weather.get("weather") or "-"
    w_hum = weather.get("humidity_pct") or "-"
    w_wind = weather.get("wind_speed") or "-"

    # repos table rows (name | stars | link)
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

          <div class="muted">CSV attachments included: repos.csv, weather.csv</div>
        </div>
      </body>
    </html>
    """
    return html

def send_html_report(attachments: list[str]) -> None:
    """Compose a multipart/alternative email (plain + HTML) with attachments."""
    if not SENDER or not APP_PASS:
        raise SystemExit("Missing MAIL_SENDER or MAIL_APP_PASSWORD in .env")

    # 1) Load data produced by your other scripts
    top_repos = read_top_repos("repos.csv", top_n=5)
    weather = read_weather("weather.csv")

    # 2) Build both plain-text fallback and rich HTML
    plain = "Daily report attached.\n- repos.csv\n- weather.csv\n"
    html = build_html(top_repos, weather)

    # 3) multipart/mixed (root) → multipart/alternative (body) + attachments
    root = MIMEMultipart("mixed")
    root["Subject"] = "Daily HTML Report: GitHub & Weather"
    root["From"] = SENDER
    root["To"] = RECEIVER

    # The body part holds plain + html alternatives (for compatibility)
    body = MIMEMultipart("alternative")
    body.attach(MIMEText(plain, "plain"))
    body.attach(MIMEText(html, "html"))
    root.attach(body)

    # 4) Add all requested attachments (CSV files)
    for path in attachments:
        attach_file(root, path)

    # 5) Send securely via Gmail SMTP (implicit SSL)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER, APP_PASS)
        server.sendmail(SENDER, [RECEIVER], root.as_string())

    print("✅ Sent HTML report with attachments.")

if __name__ == "__main__":
    try:
        send_html_report(["repos.csv", "weather.csv"])
    except Exception as e:
        print(f"❌ Failed to send HTML report: {e}") 