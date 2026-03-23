

import os
import json
from typing import Dict
from dotenv import load_dotenv
from google import genai

# FORCE PATH LOAD
load_dotenv(dotenv_path=".env")

API_KEY = os.getenv("GEMINI_API_KEY")

print("DEBUG API KEY:", API_KEY)  # TEMP DEBUG

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=API_KEY)


def classify_content(scored: Dict) -> Dict:

    texts = []

    for h in scored.get("headings", []):
        texts.append(h["text"])

    for p in scored.get("paragraphs", []):
        texts.append(p["text"])

    texts = texts[:25]

    if not texts:
        return {"classified": []}

    prompt = f"""
Classify each text into:

hero / about / services / testimonials / contact / ignore

Return JSON ONLY.

{texts}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        return {"classified": json.loads(response.text)}

    except Exception as e:
        print("[CLASSIFIER ERROR]", e)
        return {"classified": []}