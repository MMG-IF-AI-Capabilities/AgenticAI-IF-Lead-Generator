import smtplib
import csv
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

COMPANY_CSV = os.getenv("COMPANY_CSV", "qualified_company_list.csv")
RM_EMAIL = os.getenv("RM_EMAIL")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def generate_summary_message(row):
    """Generate a conversation-style summary message from a single company row."""
    company_name = row.get("companyName", "Unknown Company")
    turnover = row.get("turnover", "")
    funding_type = row.get("funding_type", "")
    recommendation = row.get("recommended_product", "")

    message = (
        f"For the turnover requirement, user replied: \"{turnover}\"\n"
        f"For the funding type requirement, user replied: \"{funding_type}\"\n"
        f"Based on this, our AI bot recommendation was: \"{recommendation}\"\n"
    )
    return message


def send_rm_email(phone, dt):
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

    message = generate_summary_message(company_details)

    subject = f"📢 Interested Lead: {company_details['companyName']}"
    body = f"""
    Hello RM,

    The following company has shown interest in our pitch:

    Analysis: 
    {company_details['qualitative_narrative']}

    Company: {company_details['companyName']}
    
    cfps_score: {company_details['cfps_score']}

    Phone: {company_details['phone']}

    Conversation Result:
      {message}
    
    The client has accepted the call at {dt}.
    Please reach out to them promptly to discuss how we can assist with their cash flow needs.

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
        print(f"Email sent to RM for {company_details['companyName']}")

