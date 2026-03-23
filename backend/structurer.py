from typing import Dict, List
from cleaner import clean_text


def build_structure(scored: Dict, classified: Dict) -> Dict:

    classified_items = classified.get("classified", [])

    hero = None
    about = None
    services = []
    testimonials = []
    contact_texts = []

    # -------------------------------
    # AI CLASSIFICATION OUTPUT
    # -------------------------------

    for item in classified_items:
        text = clean_text(item.get("text", ""))
        typ = item.get("type", "")

        if not text:
            continue

        if typ == "hero" and not hero:
            hero = text

        elif typ == "about" and not about:
            about = text

        elif typ == "services":
            services.append(text)

        elif typ == "testimonials":
            testimonials.append(text)

        elif typ == "contact":
            contact_texts.append(text)

    # -------------------------------
    # FALLBACK SYSTEM (CRITICAL)
    # -------------------------------

    headings = [clean_text(h["text"]) for h in scored.get("headings", [])]
    paragraphs = [clean_text(p["text"]) for p in scored.get("paragraphs", [])]

    business_name = clean_text(scored.get("business_name") or "Business")

    if not hero:
        for h in headings[:3]:
            if len(h.split()) >= 3:
                hero = h
                break

    if not hero:
        hero = business_name

    if not about:
        for p in paragraphs:
            if "we" in p.lower() or "our" in p.lower():
                about = p
                break

    if not about and paragraphs:
        about = paragraphs[0]

    if not services:
        services = headings[:5]

    if not testimonials:
        testimonials = [t["text"] for t in scored.get("testimonials", [])[:2]]

    # -------------------------------
    # CLEAN SERVICES
    # -------------------------------

    clean_services = []
    seen = set()

    for s in services:
        name = s.strip()

        if not name:
            continue

        if any(x in name.lower() for x in [
            "book", "call", "contact", "home", "about"
        ]):
            continue

        if name.lower() not in seen:
            seen.add(name.lower())
            clean_services.append(name)

    clean_services = clean_services[:6]

    # -------------------------------
    # BUILD FINAL STRUCTURE
    # -------------------------------

    return {
        "meta": {
            "business_name": business_name,
            "industry": "service",
            "logo_url": None,
            "existing_brand_color": None
        },
        "hero": {
            "headline": hero,
            "subheadline": "",
            "cta_primary": scored.get("cta_texts", ["Contact Us"])[0],
            "cta_secondary": None,
            "hero_image_url": None
        },
        "about": {
            "title": "About Us",
            "body": about,
            "doctor_name": None,
            "doctor_photo_url": None,
            "established_year": None
        },
        "services": [
            {"name": s, "description": None, "icon_url": None}
            for s in clean_services
        ],
        "stats": [],
        "testimonials": [
            {"quote": clean_text(t), "patient_name": None, "treatment": None}
            for t in testimonials[:3]
        ],
        "faq": [],
        "contact": {
            "phone": scored.get("contact_info", []),
            "email": [],
            "address": None,
            "hours": None
        },
        "content_confidence": 0.85
    }