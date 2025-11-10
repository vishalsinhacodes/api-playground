import os
import ssl
import mimetypes
import smtplib
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
from dotenv import load_dotenv

load_dotenv()

SENDER = os.getenv("MAIL_SENDER")
APP_PASS = os.getenv("MAIL_APP_PASSWORD")
RECEIVER = os.getenv("MAIL_RECEIVER", SENDER)

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
    
def send_mail_with_attachment(subject: str, body_text: str, attachment_path: str):
    if not SENDER or not APP_PASS or not RECEIVER:
        raise SystemExit("Missing MAIL_SENDER/MAIL_APP_PASSWORD/MAIL_RECEIVER in .env")
    
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = RECEIVER
    msg.attach(MIMEText(body_text, "plain"))
    
    attach_file(msg, attachment_path)
    
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER, APP_PASS)
        server.sendmail(SENDER, [RECEIVER], msg.as_string())
        
    print(f"Sent email with attachment: {os.path.basename(attachment_path)}")
    
if __name__ == "__main__":
    send_mail_with_attachment(
        subject="Repos csv Report",
        body_text="Attached is the latest repo csv file.",
        attachment_path="repos.csv",
    )