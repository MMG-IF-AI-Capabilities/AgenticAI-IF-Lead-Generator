from flask import Flask, request, jsonify
import csv
import os
from PersonalDetailFetch.EmailAndPhoneFetch import enrich_companies
from Personalization.Personalization import generate_if_pitch
from Personalization.SendWhatsapp import send_whatsapp_message, handle_incoming_message
from switch_to_dummy import update_to_dummy
from LeadCompaniesFetch.leadFetcher import lead_fetcher
from langchain.agents import initialize_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI

app = Flask(__name__)
COMPANY_CSV = "qualified_company_list.csv"
INITIAL_COMPANY_FETCH_INPUT = "small_companies_list.csv"


def lead_Generator_tool():
    msg = lead_fetcher(INITIAL_COMPANY_FETCH_INPUT)
    return f"{msg}  No further lead generation needed."

def enrich_tool(_):

    msg = enrich_companies(COMPANY_CSV)
    update_to_dummy() 
    return f"{msg}  No further enrichment needed."

def generate_pitch_tool(inputs: dict):
    """Generate pitch given a company dict."""
    return generate_if_pitch({
        "financials" : inputs
    }
    )

def send_whatsapp_tool(inputs: dict):
    pitch, phone = inputs["pitch"], inputs["phone"]
    sid = send_whatsapp_message(pitch, phone)
    return f"Sent to {phone} with SID {sid}"

tools = [
    Tool(
        name="LeadGenerator",
        func=lead_Generator_tool,
        description="Generate a list of small UK companies eligible for Invoice Discounting",
        return_direct=True,
    ),
    Tool(
        name="EnrichCompanies",
        func=enrich_tool,
        description="Enrich qualified_company_list.csv with Apollo + Hunter data and update dummy phones",
        return_direct=True,
    ),
    Tool(
        name="GeneratePitch",
        func=generate_pitch_tool,
        description="Generate personalized IF pitch for a company. "
                    "Input should be a the financial narrative dict with keys: companyName, chUrl, cfps_score, qualitative_narrative.",
        return_direct=True,
    ),
    Tool(
        name="SendWhatsApp",
        func=send_whatsapp_tool,
        description="Send WhatsApp pitch to a company's phone number. "
                    "Input should be a dict with keys: pitch, phone.",
        return_direct=True,
    ),
]

# --- Use Gemini Flash ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True,
)

@app.route("/run_lead", methods=["POST"])
def run_lead():
    leadgen = lead_Generator_tool()
    agent.invoke("Enrich company CSV with latest details")

    sent = []
    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            phone = row.get("phone")
            if not phone:
                continue

            pitch = generate_pitch_tool({
                "companyName": row["companyName"],
                "chUrl": row["chUrl"],
                "cfps_score": row["cfps_score"],
                "qualitative_narrative": row["qualitative_narrative"]
            })

            sid = send_whatsapp_tool({
                "pitch": pitch,
                "phone": phone,
            })

            sent.append({"company": row["companyName"], "sid": sid})

    return jsonify({"status": "completed", "sent": sent}), 200

@app.route("/resend", methods=["POST"])
def resend_whatsapp():
    data = request.get_json()
    if not data or "company" not in data or "phone" not in data:
        return jsonify({"error": "Missing company or phone"}), 400

    company_name = data["company"]
    phone = data["phone"]

    # Load the CSV and find the company row
    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
        fieldnames = reader.fieldnames.copy() if reader.fieldnames else []

    # Find the company by name and phone
    company_row = None
    for row in rows:
        if row.get("companyName") == company_name and row.get("phone") == phone:
            company_row = row
            break

    if not company_row:
        return jsonify({"error": "Company not found"}), 404

    # Generate pitch using correct fields
    pitch = generate_pitch_tool({
        "companyName": company_row["companyName"],
        "chUrl": company_row["chUrl"],
        "cfps_score": company_row["cfps_score"],
        "qualitative_narrative": company_row["qualitative_narrative"]
    })

    # Send WhatsApp message
    sid = send_whatsapp_message(pitch, phone)

    return jsonify({
        "status": "sent",
        "company": company_name,
        "phone": phone,
        "sid": sid
    }), 200


@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    return handle_incoming_message()


if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False)
