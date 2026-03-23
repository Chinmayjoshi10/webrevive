from typing import List, Dict
import re
from models import ScrapedData


# -------------------------------
# HELPER FUNCTIONS
# -------------------------------

def is_duplicate(text: str, seen: set) -> bool:
    key = text[:80].lower()
    if key in seen:
        return True
    seen.add(key)
    return False


def is_garbled(text: str) -> bool:
    non_ascii = sum(1 for c in text if ord(c) > 127)
    return (non_ascii / max(len(text), 1)) > 0.3


def contains_action_word(text: str) -> bool:
    words = ["book", "call", "contact", "visit", "get", "start"]
    return any(w in text.lower() for w in words)


def contains_service_hint(text: str) -> bool:
    keywords = [
        "service", "treatment", "care", "solution", "design",
        "development", "consulting", "repair", "implant",
        "braces", "cleaning", "therapy"
    ]
    return any(k in text.lower() for k in keywords)


def looks_like_nav(text: str) -> bool:
    nav_words = ["home", "about", "contact", "menu", "gallery", "blog"]
    return text.lower() in nav_words or len(text.split()) <= 2


# -------------------------------
# SCORERS
# -------------------------------

def score_heading(text: str, seen: set) -> int:
    score = 0

    if not text:
        return 0

    if is_duplicate(text, seen):
        return -5

    if is_garbled(text):
        return -5

    if contains_service_hint(text):
        score += 3

    if contains_action_word(text):
        score += 2

    if len(text) < 60:
        score += 2

    if looks_like_nav(text):
        score -= 3

    return score


def score_paragraph(text: str, seen: set) -> int:
    score = 0

    if not text:
        return 0

    if is_duplicate(text, seen):
        return -5

    if is_garbled(text):
        return -5

    length = len(text)

    if 50 <= length <= 300:
        score += 2

    if contains_service_hint(text):
        score += 3

    if " i " in text.lower() or text.startswith('"'):
        score += 2  # testimonial-like

    if contains_action_word(text):
        score += 1

    if length < 30:
        score -= 2

    return score


def score_image(img: Dict) -> int:
    score = 0

    src = (img.get("src") or "").lower()
    alt = (img.get("alt") or "").lower()

    if "logo" in src or "logo" in alt:
        score += 5

    if any(x in src for x in ["team", "doctor", "about"]):
        score += 4

    if any(x in alt for x in ["service", "treatment"]):
        score += 2

    if "icon" in src:
        score -= 3

    return score


def score_testimonial(text: str) -> int:
    score = 0

    if not text:
        return 0

    if " i " in text.lower():
        score += 3

    if len(text) > 50:
        score += 2

    if contains_service_hint(text):
        score += 2

    return score


# -------------------------------
# MAIN FUNCTION
# -------------------------------

def score_content(scraped: ScrapedData) -> Dict:
    """
    Returns scored content for structurer.
    """

    heading_seen = set()
    paragraph_seen = set()

    scored_headings = []
    for h in scraped.headings:
        s = score_heading(h, heading_seen)
        if s >= 2:
            scored_headings.append({"text": h, "score": s})

    scored_paragraphs = []
    for p in scraped.paragraphs:
        s = score_paragraph(p, paragraph_seen)
        if s >= 2:
            scored_paragraphs.append({"text": p, "score": s})

    scored_images = []
    for img in scraped.images:
        s = score_image(img)
        if s >= 1:
            scored_images.append({"data": img, "score": s})

    scored_testimonials = []
    for t in scraped.testimonials:
        s = score_testimonial(t)
        if s >= 2:
            scored_testimonials.append({"text": t, "score": s})

    # sort everything
    scored_headings.sort(key=lambda x: x["score"], reverse=True)
    scored_paragraphs.sort(key=lambda x: x["score"], reverse=True)
    scored_images.sort(key=lambda x: x["score"], reverse=True)
    scored_testimonials.sort(key=lambda x: x["score"], reverse=True)

    return {
        "business_name": scraped.business_name,
        "headings": scored_headings[:10],
        "paragraphs": scored_paragraphs[:10],
        "images": scored_images[:10],
        "testimonials": scored_testimonials[:5],
        "cta_texts": scraped.cta_texts,
        "contact_info": scraped.contact_info,
        "sections": scraped.sections,
        "raw": scraped  # keep full fallback
    }