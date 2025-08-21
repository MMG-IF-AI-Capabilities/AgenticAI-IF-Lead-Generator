from flask import Flask, request, jsonify
from PersonalDetailFetch.EmailAndPhoneFetch import enrich_companies
from Personalization.Personalization import generate_if_pitch
from Personalization.SendWhatsapp import send_whatsapp_message, handle_incoming_message
import csv
from switch_to_dummy import update_to_dummy

app = Flask(__name__)
COMPANY_CSV = "companies.csv"

@app.route("/run_lead", methods=["POST"])
def run_Lead():
    """Enrich companies.csv and send personalized WhatsApp pitch"""
    enrich_companies(COMPANY_CSV)
    #comment it out if you want to use real data
    update_to_dummy()

    sent = []
    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            company_name = row.get("company_name")
            company_link = row.get("company_link")
            financials = {
                "Free Cash Flow": row.get("Free_Cash_Flow"),
                "Working Capital": row.get("Working_Capital"),
                "turnover": row.get("turnover")
            }
            phone = row.get("phone")

            if phone:
                pitch = generate_if_pitch(company_name, company_link, financials)

                sid = send_whatsapp_message(pitch,phone)
                sent.append({"company": company_name, "sid": sid})

    return jsonify({"status": "completed", "sent": sent}), 200

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    return handle_incoming_message()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
