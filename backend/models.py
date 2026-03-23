from typing import List, Optional, Dict
from pydantic import BaseModel


# -------------------------------
# REQUEST MODELS
# -------------------------------

class ScrapeRequest(BaseModel):
    url: str


class AnalyzeRequest(BaseModel):
    url: str


# -------------------------------
# SCRAPED DATA (RICH + SIGNALS)
# -------------------------------

class ScrapedData(BaseModel):
    url: str
    title: Optional[str] = None
    raw_text: Optional[str] = None
    meta_description: Optional[str] = None
    screenshot_base64: Optional[str] = None

    scrape_success: bool
    error: Optional[str] = None

    # -------- STRUCTURED CONTENT --------
    headings: List[str] = []
    paragraphs: List[str] = []
    images: List[Dict] = []
    videos: List[str] = []
    links: List[Dict] = []
    sections: List[Dict] = []

    # -------- BUSINESS SIGNALS --------
    business_name: Optional[str] = None
    cta_texts: List[str] = []
    testimonials: List[str] = []
    contact_info: List[str] = []


# -------------------------------
# RESPONSES
# -------------------------------

class ScrapeResponse(BaseModel):
    success: bool
    url: str
    scraped: Optional[ScrapedData] = None
    error: Optional[str] = None


class AnalyzeResponse(BaseModel):
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None