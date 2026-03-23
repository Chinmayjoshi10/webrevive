import asyncio
import base64
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from models import ScrapedData


SCRAPE_TIMEOUT_MS = 30000


# -------------------------------
# HTML PARSER (CORE)
# -------------------------------

def _parse_html(html: str, url: str, screenshot_b64: str = None) -> ScrapedData:

    soup = BeautifulSoup(html, "html.parser")

    # -------------------------------
    # BASIC META
    # -------------------------------

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta = soup.find("meta", attrs={"name": "description"})
    meta_description = meta.get("content") if meta else None

    # -------------------------------
    # HEADINGS
    # -------------------------------

    headings = [
        h.get_text(strip=True)
        for h in soup.find_all(["h1", "h2", "h3"])
        if h.get_text(strip=True)
    ]

    # -------------------------------
    # PARAGRAPHS
    # -------------------------------

    paragraphs = [
        p.get_text(strip=True)
        for p in soup.find_all("p")
        if len(p.get_text(strip=True)) > 40
    ]

    # -------------------------------
    # IMAGES
    # -------------------------------

    images: List[Dict] = []
    for img in soup.find_all("img"):
        src = img.get("src")
        alt = img.get("alt")
        if src:
            images.append({"src": src, "alt": alt})

    # -------------------------------
    # LINKS
    # -------------------------------

    links: List[Dict] = []
    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(strip=True)

        if href and text and len(text) < 50:
            links.append({"text": text, "href": href})

    # -------------------------------
    # SECTIONS (STRUCTURED EXTRACTION)
    # -------------------------------

    sections = []

    for section in soup.find_all(["section", "div"]):
        text = section.get_text(separator=" ", strip=True)

        if len(text) < 80 or len(text) > 1000:
            continue

        heading = None
        h = section.find(["h1", "h2", "h3"])
        if h:
            heading = h.get_text(strip=True)

        sections.append({
            "heading": heading,
            "content": text[:500]
        })

    # remove duplicates
    unique_sections = []
    seen = set()

    for sec in sections:
        key = sec["content"][:100]
        if key not in seen:
            seen.add(key)
            unique_sections.append(sec)

    sections = unique_sections[:10]

    # -------------------------------
    # CLEAN TEXT
    # -------------------------------

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    raw_text = soup.get_text(separator="\n", strip=True)
    lines = [line for line in raw_text.splitlines() if line.strip()]
    raw_text = "\n".join(lines)[:10000]

    # -------------------------------
    # BUSINESS SIGNALS
    # -------------------------------

    business_name = None
    if title:
        business_name = title.split("|")[0].strip()
    elif headings:
        business_name = headings[0]

    # CTA
    cta_texts = []
    for btn in soup.find_all(["button", "a"]):
        text = btn.get_text(strip=True)
        if text and len(text) < 30:
            if any(word in text.lower() for word in ["book", "call", "contact", "appointment"]):
                cta_texts.append(text)

    # Testimonials
    testimonials = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if '"' in text or "patient" in text.lower():
            if 40 < len(text) < 300:
                testimonials.append(text)

    # Contact info
    contact_info = []
    for text in raw_text.split("\n"):
        if any(x in text.lower() for x in ["@", "+91", "phone", "email", "address"]):
            contact_info.append(text)

    print(f"[SCRAPER] headings={len(headings)} sections={len(sections)}")

    return ScrapedData(
        url=url,
        title=title,
        raw_text=raw_text,
        meta_description=meta_description,
        screenshot_base64=screenshot_b64,
        scrape_success=True,

        headings=headings[:20],
        paragraphs=paragraphs[:20],
        images=images[:15],
        videos=[],
        links=links[:20],
        sections=sections,

        business_name=business_name,
        cta_texts=cta_texts[:5],
        testimonials=testimonials[:5],
        contact_info=contact_info[:5],
    )


# -------------------------------
# FALLBACK (HTTP)
# -------------------------------

async def _fallback_scrape(url: str) -> ScrapedData:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(url)

        return _parse_html(res.text, url)

    except Exception as e:
        return ScrapedData(
            url=url,
            scrape_success=False,
            error=str(e),
        )


# -------------------------------
# MAIN SCRAPER
# -------------------------------

async def scrape_website(url: str) -> ScrapedData:

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    print(f"[SCRAPER] Start → {url}")

    try:
        async with async_playwright() as pw:

            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(url, timeout=SCRAPE_TIMEOUT_MS)
            await page.wait_for_selector("body", timeout=10000)

            await asyncio.sleep(1)

            screenshot = await page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(screenshot).decode()

            html = await page.content()

            await browser.close()

        return _parse_html(html, url, screenshot_b64)

    except PlaywrightTimeout:
        print("[SCRAPER] Timeout → fallback")
        return await _fallback_scrape(url)

    except Exception as e:
        print(f"[SCRAPER] Error → fallback: {e}")
        return await _fallback_scrape(url)