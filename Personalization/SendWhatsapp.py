from flask import request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import threading
from emailRM import send_rm_email
from ai_tools import classify_intent, ai_generate_reply, get_csv_context, update_csv_context, update_response_column, generate_recommendation


TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
COMPANY_CSV = "qualified_company_list.csv"

pending_timers = {}


def send_whatsapp_message(message_body: str, receiver_number: str):
    """Send WhatsApp message via Twilio API and start 2 min timeout timer only if applicable."""
    
    message = client.messages.create(
        body=message_body,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=f"whatsapp:{receiver_number}"
    )

    phone_normalized = receiver_number.replace("whatsapp:", "")

    context = get_csv_context(phone_normalized)
    stage = context.get("stage", 0)
    response = context.get("response", "")

 
    if phone_normalized in pending_timers:
        pending_timers[phone_normalized].cancel()
        del pending_timers[phone_normalized]

    if stage != 4 and response.lower() != "not interested":
        #timer that I've set for no response
        timer = threading.Timer(600, mark_no_response, args=[phone_normalized])
        timer.start()
        pending_timers[phone_normalized] = timer
        print(f"Sent WhatsApp message to {phone_normalized}")
    else:
        print(f"Sent WhatsApp message to {phone_normalized}. Timer not started: stage={stage} response={response}")

    return message.sid


def mark_no_response(phone):
    update_response_column(phone, "No Response")
    print(f"No response received from {phone}. Marked as 'No Response'.")

    if phone in pending_timers:
        pending_timers[phone].cancel()
        del pending_timers[phone]


def handle_incoming_message():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    phone = from_number.replace("whatsapp:", "")

    context = get_csv_context(phone)
    stage = context.get("stage", 0)
    turnover = context.get("turnover", "")
    funding_type = context.get("funding_type", "")
    # recommended_product = context.get("recommended_product", "")
    # slot = context.get("slot", "")

    intent = classify_intent(incoming_msg)
    resp = MessagingResponse()
    
    if intent == "NotInterested":
        update_csv_context(phone, turnover="", funding_type="", recommended_product="", slot="", stage=stage)
        update_response_column(phone,"Not Interested")
        send_whatsapp_message("I understand. No problem, Thank you for your time!", phone)
        return str(resp)
    
    if intent == "Question":
        ai_response = ai_generate_reply(stage, "Question", incoming_msg, phone)
        send_whatsapp_message(ai_response, phone)
        return str(resp)

    if stage in [0, 1]:
        if intent == "RequirementAnswer" or intent == "Interested":
            if stage == 0 and intent!="Interested":
                update_csv_context(phone, turnover=incoming_msg, stage=1)
            elif stage == 1 and intent!="Interested":
                update_csv_context(phone, funding_type=incoming_msg.lower(), stage=2)

            context = get_csv_context(phone)
            turnover = context.get("turnover")
            funding_type = context.get("funding_type")

            if turnover and funding_type:
                recommendation = generate_recommendation(turnover, funding_type, phone)
                update_csv_context(phone, recommended_product=recommendation, stage=2)
                send_whatsapp_message(recommendation, phone)
            else:
                next_stage = 0 if not turnover else 1
                ai_response = ai_generate_reply(next_stage, "Answer", incoming_msg, phone)
                send_whatsapp_message(ai_response, phone)
            return str(resp)

    if stage == 2:
        if intent == "Interested" or intent == "RequirementAnswer":
            update_csv_context(phone, stage=3)
            send_whatsapp_message("Great! Would you like to schedule a call with your NatWest Relationship Manager? Please share a date and time.", phone)
        else:
            update_response_column(phone,"Not Interested")
            send_whatsapp_message("No worries! If you change your mind, feel free to reach out anytime.", phone)
        return str(resp)
  
    if stage == 3 and intent != "NotInterested":
        dt = ai_generate_reply(3, "Answer", incoming_msg, phone)
        if dt != None:
            update_csv_context(phone, slot=dt, stage=4)
            update_response_column(phone,"Interested")
            send_rm_email(phone, dt)
            send_whatsapp_message(f"Perfect! Your call is scheduled for {dt}. Thank you for your time!", phone)

        else:
            send_whatsapp_message("I couldn't catch the date and time. Please share it like 'Tuesday at 3 pm'.", phone)
        return str(resp)

    send_whatsapp_message("Thanks! Could you please clarify your message?", phone)
    return str(resp)
