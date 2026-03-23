"""
WebRevive AI Client (Production)
================================

Features:
- OpenRouter integration (OpenAI-compatible)
- Multi-model rotation with failover
- JSON schema enforcement
- Retry handling (rate limits + invalid JSON)
- Task-aware routing
- Deterministic + fallback-safe

Env Required:
- OPENROUTER_API_KEY
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, List

from openai import OpenAI

# ---------------------------
# CONFIG
# ---------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is required")

BASE_URL = "https://openrouter.ai/api/v1"

client = OpenAI(
    base_url=BASE_URL,
    api_key=OPENROUTER_API_KEY
)

logger = logging.getLogger("ai_client")
logger.setLevel(logging.INFO)


# ---------------------------
# MODEL POOL
# ---------------------------

PRIMARY_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "mistralai/codestral-2501:free"
]

TASK_MODEL_MAP = {
    "content_refinement": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/codestral-2501:free"
    ],
    "design_spec": [
        "openai/gpt-oss-120b:free",
        "meta-llama/llama-3.3-70b-instruct:free"
    ],
    "color_palette": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/codestral-2501:free"
    ]
}


# ---------------------------
# HELPERS
# ---------------------------

def _strip_markdown(text: str) -> str:
    """
    Removes ```json ... ``` wrappers
    """
    if not text:
        return text

    text = text.strip()

    if text.startswith("```"):
        text = text.split("```", 1)[-1]
        text = text.rsplit("```", 1)[0]

    return text.strip()


def _parse_json(text: str) -> Dict[str, Any]:
    cleaned = _strip_markdown(text)
    return json.loads(cleaned)


def _is_rate_limit_error(e: Exception) -> bool:
    return "429" in str(e) or "rate limit" in str(e).lower()


def _get_model_sequence(task_type: Optional[str]) -> List[str]:
    if task_type and task_type in TASK_MODEL_MAP:
        # ensure fallback always includes Codestral at end
        return TASK_MODEL_MAP[task_type] + [
            m for m in PRIMARY_MODELS if m not in TASK_MODEL_MAP[task_type]
        ]
    return PRIMARY_MODELS


# ---------------------------
# CORE FUNCTION
# ---------------------------

def call_ai(
    prompt: str,
    json_schema: Dict[str, Any],
    task_type: Optional[str] = None,
    max_retries_per_model: int = 2
) -> Dict[str, Any]:
    """
    Core AI call with:
    - model rotation
    - schema enforcement
    - retries

    Args:
        prompt: full prompt string
        json_schema: JSON schema dict
        task_type: optional routing hint
    """

    models = _get_model_sequence(task_type)

    last_error = None

    while True:  # full cycle retry loop (after all models exhausted)
        for model in models:
            logger.info(f"[AI] Trying model: {model}")

            for attempt in range(max_retries_per_model):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a strict JSON generator. Output ONLY valid JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        response_format={
                            "type": "json_schema",
                            "json_schema": json_schema
                        },
                        temperature=0.2
                    )

                    raw_text = response.choices[0].message.content

                    try:
                        parsed = _parse_json(raw_text)

                        logger.info(f"[AI SUCCESS] model={model}")
                        return parsed

                    except Exception as parse_error:
                        logger.warning(
                            f"[AI PARSE ERROR] model={model} attempt={attempt+1}"
                        )

                        if attempt == max_retries_per_model - 1:
                            raise parse_error
                        continue

                except Exception as e:
                    last_error = e

                    # Rate limit → try next model
                    if _is_rate_limit_error(e):
                        logger.warning(f"[AI RATE LIMIT] model={model}")
                        break  # break retry loop → next model

                    # Other errors → retry same model
                    logger.warning(
                        f"[AI ERROR] model={model} attempt={attempt+1} error={str(e)}"
                    )

                    if attempt == max_retries_per_model - 1:
                        break

                    time.sleep(2)

            # move to next model

        # All models exhausted → wait + retry
        logger.error("[AI] All models exhausted. Sleeping 60s before retry...")
        time.sleep(60)