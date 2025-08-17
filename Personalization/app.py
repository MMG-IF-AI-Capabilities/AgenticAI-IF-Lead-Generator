from flask import Flask, request, jsonify
from Personalization import generate_if_pitch
from SendWhatsapp import send_whatsapp_message, handle_incoming_message
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route("/send_pitch", methods=["POST"])
def send_pitch():
    data = request.get_json()
    company_name = data.get("company_name")
    company_link = data.get("company_link")
    financials = data.get("financials", {})

    pitch_message = generate_if_pitch(company_name, company_link, financials)
    sid = send_whatsapp_message(pitch_message)

    return jsonify({"status": "sent", "sid": sid, "message": pitch_message}), 200

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    return handle_incoming_message()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
