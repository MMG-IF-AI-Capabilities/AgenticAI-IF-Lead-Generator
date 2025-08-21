import smtplib
import csv
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

COMPANY_CSV = os.getenv("COMPANY_CSV", "companies.csv")
RM_EMAIL = os.getenv("RM_EMAIL")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def send_rm_email(phone):
    """Send email to RM when a company shows interest."""
    company_details = None
    phone_normalized = phone.replace("whatsapp:", "")

    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            if row.get("phone") == phone_normalized:
                company_details = row
                break

    if not company_details:
        print("No matching company found.")
        return

    subject = f"📢 Interested Lead: {company_details['company_name']}"
    body = f"""
    Hello RM,

    The following company has shown interest in our pitch:

    Company: {company_details['company_name']}
    Link: {company_details['company_link']}
    Free Cash Flow: {company_details['Free_Cash_Flow']}
    Working Capital: {company_details['Working_Capital']}
    Turnover: {company_details['turnover']}
    Phone: {company_details['phone']}

    Please reach out to them at the earliest.

    Regards,
    Your Lead Bot
    """

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = RM_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        print(f"Email sent to RM for {company_details['company_name']}")

