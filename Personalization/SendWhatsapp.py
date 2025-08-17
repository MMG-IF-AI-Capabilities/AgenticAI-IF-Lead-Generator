from flask import request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

RECEIVER_WHATSAPP_NUMBER = 'whatsapp:+91XXXXX'  # Replace with your own WhatsApp number
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp_message(message_body: str):
    """Send WhatsApp message via Twilio API."""
    message = client.messages.create(
        body=message_body,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=RECEIVER_WHATSAPP_NUMBER
    )
    return message.sid

def handle_incoming_message():
    """Handle incoming WhatsApp replies from users."""
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')

    print(f"📩 Received message from {from_number}: {incoming_msg}")

    resp = MessagingResponse()
    reply = resp.message()

    if incoming_msg == "1":
        reply.body("✅ Thanks! Here is the link to apply: https://deekr.com/apply")
    elif incoming_msg == "2":
        reply.body("🙏 Thanks for your response. Have a great day!")
    else:
        reply.body("⚠️ Invalid input. Please reply with 1 (Interested) or 2 (Not Interested).")

    return str(resp)
