
import os, json
from typing import List
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_a_plus_digest(subject: str, html_content: str, recipients: List[str]):
    api_key = os.getenv("SENDGRID_API_KEY", "")
    if not api_key:
        return {"error": "SENDGRID_API_KEY not set"}
    if not recipients:
        return {"error": "No recipients provided"}
    message = Mail(
        from_email=os.getenv("DIGEST_FROM_EMAIL", "no-reply@vega.local"),
        to_emails=recipients,
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(api_key)
        resp = sg.send(message)
        return {"status": resp.status_code}
    except Exception as e:
        return {"error": str(e)}
