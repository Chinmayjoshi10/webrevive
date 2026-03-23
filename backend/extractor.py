

import os
import json
from typing import Dict
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

print("DEBUG API KEY:", API_KEY)

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=API_KEY)

# -------------------------------
# SAFE GEMINI CALL
# -------------------------------

def call_gemini(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print("[GEMINI ERROR]", e)
        return None


# -------------------------------
# MAIN REFINEMENT FUNCTION
# -------------------------------

def refine_structure(structure: Dict) -> Dict:

    prompt = f"""
You are a professional website copywriter.

Your job is to IMPROVE the content of a business website.

STRICT RULES:
- DO NOT add fake information
- DO NOT hallucinate
- ONLY improve clarity, tone, and professionalism
- Keep original meaning exactly
- Make it modern, premium, and clean

Return JSON ONLY in SAME structure.

INPUT:
{json.dumps(structure, indent=2)}
"""

    raw_output = call_gemini(prompt)

    if not raw_output:
        return structure  # fallback

    try:
        refined = json.loads(raw_output)
        return refined
    except Exception as e:
        print("[REFINE PARSE FAILED]")
        return structure