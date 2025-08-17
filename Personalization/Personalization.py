import json
from typing import Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv
import os

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def query_gemini(prompt: str, model: str = "gemini-1.5-flash") -> str:
    """Query Gemini API for content generation."""
    model_instance = genai.GenerativeModel(model)
    response = model_instance.generate_content(prompt)
    return response.text.strip() if response and response.text else "No response."

def generate_if_pitch(company_name: str, company_link: str, financials: Dict[str, Any]) -> str:
    """Generate personalized WhatsApp pitch message."""
    prompt = f"""
    You are a financial advisor creating a personalized sales pitch 
    for an Invoice Discounting (IF) product.

    Company: {company_name}
    Website: {company_link}
    Financials: {json.dumps(financials, indent=2)}

    STRICT RULES:
    - Use ONLY the provided financials.
    - Do NOT make up or assume numbers.
    - If a metric is missing, explicitly say "Not Available".

    Task:
    1. Create a short, conversational WhatsApp pitch.
    2. End with: "If interested, reply with 1. If not, reply with 2."
    """
    return query_gemini(prompt)
