from flask import request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import threading
from emailRM import send_rm_email

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
COMPANY_CSV = "companies.csv"

# --- Global dict to track timers ---
pending_timers = {}


def send_whatsapp_message(message_body: str, receiver_number: str):
    """Send WhatsApp message via Twilio API and start 2 min timeout timer."""
    message = client.messages.create(
        body=message_body,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=f"whatsapp:{receiver_number}"
    )

    # Start a 2-minute timer to auto-mark "No Response"
    phone_normalized = receiver_number.replace("whatsapp:", "")
    timer = threading.Timer(120, mark_no_response, args=[phone_normalized])
    timer.start()

    # Store timer so we can cancel it if user replies
    pending_timers[phone_normalized] = timer

    print(f"📤 Sent WhatsApp message to {phone_normalized}. Waiting 2 minutes for reply...")

    return message.sid


def mark_no_response(phone):
    """Mark 'No Response' if timer expires and no reply received."""
    update_response_in_csv(phone, "No Response")

    # Log clearly
    print(f"⏰ Timeout: No response received from {phone} after 2 minutes. Marked as 'No Response'.")

    # Remove expired timer from dict to free memory
    if phone in pending_timers:
        del pending_timers[phone]


def update_response_in_csv(phone, response):
    """Update the reply into companies.csv based on phone number."""
    rows = []
    updated = False

    phone = phone.replace("whatsapp:", "")  # normalize

    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        if "response" not in fieldnames:
            fieldnames.append("response")

        for row in reader:
            if row.get("phone") and row["phone"] == phone:
                row["response"] = response
                updated = True
            rows.append(row)

    with open(COMPANY_CSV, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if updated:
        print(f"Updated CSV: {phone} -> {response}")
    else:
        print(f"No match found in CSV for phone {phone}")


def handle_incoming_message():
    """Handle incoming WhatsApp replies from users."""
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')

    print(f" Received message from {from_number}: {incoming_msg}")

    response_map = {"1": "Interested", "2": "Not Interested"}
    response = response_map.get(incoming_msg, "Invalid")

    phone_normalized = from_number.replace("whatsapp:", "")

    # --- Cancel pending timer if response received ---
    if phone_normalized in pending_timers:
        pending_timers[phone_normalized].cancel()
        del pending_timers[phone_normalized]

    # Update CSV
    update_response_in_csv(from_number, response)

    resp = MessagingResponse()
    reply = resp.message()

    if response == "Interested":
        reply.body("Thanks! Here is the link to apply: https://deekr.com/apply. Our RM will contact you shortly.")

        with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if row.get("phone") == phone_normalized:
                    send_rm_email(row["phone"])
                    break

    elif response == "Not Interested":
        reply.body("Thanks for your response. Have a great day!")
    else:
        reply.body("Invalid input. Please reply with 1 (Interested) or 2 (Not Interested).")

    return str(resp)
