import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def query_gemini(prompt: str, model: str = "gemini-1.5-flash") -> str:
    model_instance = genai.GenerativeModel(model)
    response = model_instance.generate_content(prompt)
    return response.text.strip() if response and response.text else "No response."

def generate_if_pitch(financials: dict) -> str:
    """Generate a professional and personalized Invoice Discounting pitch under 1600 characters."""
    prompt = f"""
    You are a trusted financial advisor assisting businesses with cash flow solutions.
    Craft a warm, professional, and personalized WhatsApp message to introduce our Invoice Discounting (IF) service.

    Financial Details: {json.dumps(financials, indent=2)}

    Guidelines:
    - The message must be under 1600 characters.
    - Use only the provided financial data and, where appropriate, infer general context from the company's website such as industry, operations, scale, products, or customers.
    - Do NOT invent or assume specific financial figures. If any data point is missing, clearly state "Not Available".
    - Explain in a clear and approachable way how IF can help address cash flow challenges specific to this company.
    - Provide step-by-step information on how the service works, avoiding technical jargon.
    - Keep the tone professional, empathetic, and supportive — as if you are a consultant offering helpful advice.
    - End the message by asking the end user if they are Interested or not to continue the conversation.

    Structure:
    1. Begin with a brief, friendly introduction addressing the company by name.
    2. Summarize the company’s business or industry context, based on available information.
    3. Highlight the numbers mentioned in the narrative for more realisitc analysis based pitch.
    4. Show how IF specifically helps and the benefits it brings.
    5. Outline how the service works in simple, actionable steps.
    6. Wrap up with a courteous invitation to connect further.

    Ensure the message reads naturally, is human-centered, and reflects understanding and care.
    """

    return query_gemini(prompt)