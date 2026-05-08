from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from dotenv import load_dotenv
load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL       = os.getenv("FROM_EMAIL")
TO_EMAIL         = os.getenv("TO_EMAIL")

if not SENDGRID_API_KEY:
    raise ValueError("SENDGRID_API_KEY not set")

print("Sending test email...")

message = Mail(
    from_email   = FROM_EMAIL,
    to_emails    = TO_EMAIL,
    subject      = "CPRP Test — Email is working!",
    html_content = """
    <h2>Email is working!</h2>
    <p>Your CPRP notification system is set up correctly.</p>
    <p>This email was sent from your Python project.</p>
    """
)

try:
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(f"Email sent! Status code: {response.status_code}")
    print(f"Check your inbox at: {TO_EMAIL}")
except Exception as e:
    print(f"Failed: {e}")
    print("\nCommon fixes:")
    print("1. API key wrong → copy again from SendGrid dashboard")
    print("2. Sender not verified → go to SendGrid → Settings → Sender Authentication")
    print("3. Check spam folder")