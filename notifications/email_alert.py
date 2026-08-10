import os
import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_alert_email(subject: str, body: str) -> dict:
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("ALERT_RECIPIENT")

    if not all([gmail_address, gmail_app_password, recipient]):
        return {
            "sent": False,
            "reason": "Missing GMAIL_ADDRESS, GMAIL_APP_PASSWORD, or ALERT_RECIPIENT env vars",
        }

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = recipient

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, [recipient], msg.as_string())
        return {"sent": True, "to": recipient}
    except Exception as e:
        return {"sent": False, "reason": str(e)}