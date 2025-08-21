import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def query_gemini(prompt: str, model: str = "gemini-1.5-flash") -> str:
    """Query Gemini API for pitch generation."""
    model_instance = genai.GenerativeModel(model)
    response = model_instance.generate_content(prompt)
    return response.text.strip() if response and response.text else "No response."

def generate_if_pitch(company_name: str, company_link: str, financials: dict) -> str:
    """Generate a strong, personalized IF pitch under 1600 characters."""
    prompt = f"""
    You are an expert financial advisor. Your goal is to craft a personalized
    WhatsApp pitch for our Invoice Discounting (IF) product.

    Company: {company_name}
    Website: {company_link}
    Financials: {json.dumps(financials, indent=2)}

    STRICT RULES:
    - The final pitch MUST be under 1600 characters total.
    - Use ONLY verified details from the financials and, if available, infer context
      from the company's website (industry, operations, scale, products, customers).
    - Do NOT fabricate financial numbers. If a metric is missing, explicitly state "Not Available".
    - Clearly explain WHY our Invoice Discounting product is valuable for this specific company.
    - Explain HOW it works in simple terms (step-by-step).
    - Make the pitch conversational, consultative, and persuasive.
    - End with: "If interested, reply with 1. If not, reply with 2."

    Task:
    1. Start with a short, personalized greeting mentioning the company.
    2. Summarize what the company does (from website/industry context).
    3. Tie their business model/financials to common cash flow challenges.
    4. Show why IF solves their problems and its benefits.
    5. Explain briefly how IF works (without jargon).
    6. Ensure total response length < 1600 characters.
    """

    return query_gemini(prompt)
