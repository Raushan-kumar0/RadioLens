"""
Email delivery for MRIG.

Sends the generated X-ray PDF report to the patient's email using yagmail.

Requires MRIG_SENDER_EMAIL and MRIG_SENDER_APP_PASSWORD environment
variables (a Gmail address + an App Password, NOT your normal Gmail
password: https://support.google.com/accounts/answer/185833).
Never hardcode credentials in source.
"""

import os

import yagmail
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.environ.get("MRIG_SENDER_EMAIL")
SENDER_APP_PASSWORD = os.environ.get("MRIG_SENDER_APP_PASSWORD")


def sendMail(receiver):
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        print(
            "Email not sent: set MRIG_SENDER_EMAIL and MRIG_SENDER_APP_PASSWORD "
            "(see .env.example) to enable report emailing."
        )
        return

    body = "Your X-Ray Report - MRIG"
    filename = "static/output.pdf"

    try:
        yag = yagmail.SMTP(SENDER_EMAIL, SENDER_APP_PASSWORD)
        yag.send(
            to=receiver,
            subject="X-Ray Report",
            contents=body,
            attachments=filename,
        )
    except Exception as exc:
        # Don't let a mail failure take down the request thread it's run on
        print(f"Failed to email report to {receiver}: {exc}")
