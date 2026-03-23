# backend/cleaner.py

import ftfy


def clean_text(text: str) -> str:
    if not text:
        return ""
    return ftfy.fix_text(text).strip()