import os
import csv
from datetime import datetime
from dateutil import parser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from functools import lru_cache

from datetime import datetime



COMPANY_CSV = "qualified_company_list.csv"

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    max_output_tokens=1000, streaming=False
)

def get_csv_context(phone):
    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            if row.get("phone") == phone:
                stage_value = row.get("stage")
                stage = int(stage_value) if stage_value and stage_value.isdigit() else 0
                return {
                    "turnover": row.get("turnover", ""),
                    "funding_type": row.get("funding_type", ""),
                    "recommended_product": row.get("recommended_product", ""),
                    "slot": row.get("slot", ""),
                    "stage": stage,
                    "response": row.get("response", "")
                }
    return {"turnover": "", "funding_type": "", "recommended_product": "", "slot": "", "stage": 0, "response": ""}



def update_csv_context(phone, turnover=None, funding_type=None, recommended_product=None, slot=None, stage=None):
    """Update CSV context for given phone."""
    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
        fieldnames = reader.fieldnames.copy() if reader.fieldnames else []

    for col in ["turnover", "funding_type", "recommended_product", "slot", "stage"]:
        if col not in fieldnames:
            fieldnames.append(col)

    updated = False
    for row in rows:
        if row.get("phone") == phone:
            if turnover is not None:
                row["turnover"] = turnover
            if funding_type is not None:
                row["funding_type"] = funding_type
            if recommended_product is not None:
                row["recommended_product"] = recommended_product
            if slot is not None:
                row["slot"] = slot
            if stage is not None:
                row["stage"] = stage
            updated = True
            break

    if not updated:
        new_row = {field: "" for field in fieldnames}
        new_row.update({
            "phone": phone,
            "turnover": turnover or "",
            "funding_type": funding_type or "",
            "recommended_product": recommended_product or "",
            "slot": slot or "",
            "stage": stage or 0
        })
        rows.append(new_row)

    with open(COMPANY_CSV, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def classify_intent(message: str) -> str:
    prompt = ChatPromptTemplate.from_template(f"""
You are an AI assistant helping classify the user's intent in a finance-related conversation.

Classify the following message into one of these four labels based on the user's intent:
- RequirementAnswer: The user is providing an answer to a required question like turnover or funding type or time slot for meeting.
- Question: The user is asking for information or clarification.
- Interested: The user expresses interest in proceeding but has not answered the requirement question yet.
- NotInterested: The user expresses that they are not interested in proceeding.

Message: "{message}"

If the message implies that the user is choosing between funding types (e.g. credit-based or asset-based funding), or providing details like turnover, classify it as RequirementAnswer.

Reply ONLY with one of these words ["RequirementAnswer", "Question", "Interested", "NotInterested"].
""")
    chain = prompt | llm
    response = chain.invoke({})
    label = response.content.strip()
    if label not in ["RequirementAnswer", "Question", "Interested", "NotInterested"]:
        return "Question"
    return label

@lru_cache(maxsize=128)
def cached_response(prompt_text: str) -> str:
    """Cache responses to avoid repeating expensive queries."""
    prompt = ChatPromptTemplate.from_template(prompt_text)
    chain = prompt | llm
    try:
        response = chain.invoke({})
        return response.content.strip()
    except Exception as e:
        print("AI generation failed:", e)
        return "Sorry, I couldn't process that right now. Please try again."
    
def generate_recommendation_prompt(turnover: str, funding_type: str, phone: str) -> str:
    """Create a prompt for recommending the correct NatWest product."""
    prompt_text = f"""
You are an AI relationship manager for NatWest Invoice Finance.
Use ONLY official information from the NatWest website.


User details:
- Turnover: {turnover or "None"}
- Funding type: {funding_type or "None"}

Instructions:
1. Based on the turnover and funding type, recommend the correct NatWest product using official information from these websites and explain why the product suits their needs:
   - https://www.natwest.com/business/loans-and-finance/invoice-discounting.html
   - https://www.natwest.com/business/loans-and-finance/asset-based-lending.html
2. Provide the recommendation clearly with the correct link.
3. If the user responds with free-text instead of choosing one of the two options, classify the message based on the content:
   - "Credit-Based Funding" – where funding is based on the borrower's creditworthiness, cash flow, or credit score.
   - "Asset-Based Funding" – where funding is secured using tangible assets like property, equipment, or inventory as collateral.
   Classify accordingly and proceed as if they selected that option.
4. Do not hallucinate or guess. Only recommend if both turnover and funding type are provided.
5. If you cannot recommend based on the information, say: "I am unable to recommend a product based on the information provided. Would you like to speak to a NatWest Relationship Manager for further assistance?"
"""
    return prompt_text

def generate_recommendation(turnover: str, funding_type: str, phone: str) -> str:
    """Use the LLM to generate a recommendation based on turnover and funding type."""
    prompt_text = generate_recommendation_prompt(turnover, funding_type, phone)
    return cached_response(prompt_text)


def ai_generate_reply(stage: int, intent: str, user_message: str, phone: str):
    context = get_csv_context(phone)
    turnover = context.get("turnover", "")
    funding_type = context.get("funding_type", "")
    recommended_product = context.get("recommended_product", "")
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prompt_text = f"""
You are an AI relationship manager for NatWest Invoice Finance.
Use ONLY official information from the NatWest website.

Today's date and time is: {current_datetime}

Conversation context:
- Stage: {stage}
- Turnover: {turnover or "None"}
- Funding type: {funding_type or "None"}
- Recommended product: {recommended_product or "None"}

User intent: {intent}
User message: "{user_message}"

Instructions:
1. If the message is a question, answer it fully and factually using information from NatWest's official website.
2. If the intent is Interested, proceed to ask for missing requirements as per the stage.
3. If a required detail is missing, ask for it as follows in the following IF sequence(Always check the turnover first, if it is there then check funding type):
   - If turnover is missing, ask for the turnover amount.
   - If funding type is missing, ask only: "Are you looking for credit-based funding or asset-based funding?" Do NOT ask in any other way.
4. If the user responds with free-text instead of choosing one of the two options, classify the message based on the content:
   - "Credit-Based Funding" – where funding is based on the borrower's creditworthiness, cash flow, or credit score.
   - "Asset-Based Funding" – where funding is secured using tangible assets like property, equipment, or inventory as collateral.
   Classify accordingly and proceed as if they selected that option.
5. Ask only one missing requirement at a time.
6. Keep the conversation natural, helpful, and aligned strictly with official details from the below NatWest’s websites.
   - https://www.natwest.com/business/loans-and-finance/invoice-discounting.html
   - https://www.natwest.com/business/loans-and-finance/asset-based-lending.html
   - https://www.natwest.com/business/loans-and-finance/invoice-finance.html
7. Do not hallucinate, guess, or ask for unnecessary information.
8. If the stage is 3, extract a future date and time from the user's free text date and time reply. Return only the date-time in ISO format 'YYYY-MM-DD HH:MM:SS'. If no valid future date is found, reply with 'None'
9. If the user asks any question or shares information unrelated to invoice finance or outside the context provided in the above links, politely inform them:
   "I'm here to assist with invoice finance related queries only, using information from the official NatWest invoice finance websites. Unfortunately, I can't provide details or answer questions outside this scope.
Respond appropriately based on the context.
"""
    return cached_response(prompt_text)

def update_response_column(phone: str, new_response: str) -> None:
    """Update the 'response' column for the company with the given phone number."""
    phone_normalized = phone.replace("whatsapp:", "")

    with open(COMPANY_CSV, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
        fieldnames = reader.fieldnames

    updated = False
    for row in rows:
        if row.get("phone") == phone_normalized:
            row["response"] = new_response
            updated = True
            break

    if updated:
        with open(COMPANY_CSV, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
