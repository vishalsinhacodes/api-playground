import os
import ssl
import smtplib
import mimetypes
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
from dotenv import load_dotenv

# 1) Load secrets from .env (keeps credentials out of code)
load_dotenv()
SENDER = os.getenv("MAIL_SENDER")             # your Gmail address
APP_PASS = os.getenv("MAIL_APP_PASSWORD")     # 16-char App Password
RECEIVER = os.getenv("MAIL_RECEIVER", SENDER) # default to yourself

def attach_file(msg: MIMEMultipart, filepath: str) -> None:
    """Attach any file type safely to the email."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Attachment not found: {filepath}")

    # Detect proper MIME type (e.g., text/csv). Fallback to binary.
    ctype, encoding = mimetypes.guess_type(filepath)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    with open(filepath, "rb") as f:
        part = MIMEBase(maintype, subtype)
        part.set_payload(f.read())

    encoders.encode_base64(part)  # make attachment email-safe
    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(filepath)}"')
    msg.attach(part)

def send_mail_with_attachments(subject: str, body_text: str, attachments: list[str]) -> None:
    """Build the email, add multiple attachments, and send via Gmail SMTP over SSL."""
    if not SENDER or not APP_PASS:
        raise SystemExit("Missing MAIL_SENDER or MAIL_APP_PASSWORD in .env")

    msg = MIMEMultipart()  # container for body + attachments
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = RECEIVER

    # Plain-text body (easy to extend to HTML later)
    msg.attach(MIMEText(body_text, "plain"))

    # Add all files passed in
    for path in attachments:
        attach_file(msg, path)

    # Encrypted connection to Gmail SMTP (implicit SSL on 465)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER, APP_PASS)
        server.sendmail(SENDER, [RECEIVER], msg.as_string())

    names = ", ".join(os.path.basename(p) for p in attachments)
    print(f"Sent email with attachments: {names}")

if __name__ == "__main__":
    # Send both CSVs together
    try:
        send_mail_with_attachments(
            subject="Daily Reports: GitHub Repos & Weather",
            body_text=(
                "Attached are today's reports:\n"
                "- repos.csv (GitHub repositories summary)\n"
                "- weather.csv (current weather snapshot)\n"
            ),
            attachments=["repos.csv", "weather.csv"],
        )
    except Exception as e:
        print(f"Failed to send email: {e}")
