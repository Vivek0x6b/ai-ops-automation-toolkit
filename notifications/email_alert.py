import os
import requests
from dotenv import load_dotenv

load_dotenv()

RESEND_API_URL = "https://api.resend.com/emails"
FROM_ADDRESS = "AI Ops Toolkit <onboarding@resend.dev>"


def send_alert_email(subject: str, body: str) -> dict:
    api_key = os.environ.get("RESEND_API_KEY")
    recipient = os.environ.get("ALERT_RECIPIENT")

    if not all([api_key, recipient]):
        return {
            "sent": False,
            "reason": "Missing RESEND_API_KEY or ALERT_RECIPIENT env vars",
        }

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_ADDRESS,
                "to": [recipient],
                "subject": subject,
                "text": body,
            },
            timeout=10,
        )
        if response.status_code in (200, 201):
            return {"sent": True, "to": recipient, "id": response.json().get("id")}
        else:
            return {
                "sent": False,
                "reason": f"Resend API returned {response.status_code}: {response.text}",
            }
    except requests.RequestException as e:
        return {"sent": False, "reason": str(e)}


if __name__ == "__main__":
    result = send_alert_email(
        subject="[TEST] AI Ops Toolkit alert test",
        body="This is a test alert from the AI Ops Automation Toolkit, sent via Resend.",
    )
    print(result)