import asyncio
import sys

# Windows async fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    ScrapeRequest,
    ScrapeResponse,
    AnalyzeRequest,
    AnalyzeResponse,
)

from scraper import scrape_website
from scorer import score_content
from classifier import classify_content
from structurer import build_structure
from extractor import refine_structure


# -------------------------------
# APP INIT
# -------------------------------

app = FastAPI(
    title="WebRevive API",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------
# HEALTH
# -------------------------------

@app.get("/")
def root():
    return {"status": "WebRevive API running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------------
# SCRAPE ONLY
# -------------------------------

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(request: ScrapeRequest):

    if not request.url:
        raise HTTPException(status_code=400, detail="URL required")

    print(f"[SCRAPE] → {request.url}")

    scraped = await scrape_website(request.url)

    return ScrapeResponse(
        success=scraped.scrape_success,
        url=request.url,
        scraped=scraped,
        error=scraped.error,
    )


# -------------------------------
# ANALYZE (INTELLIGENCE PIPELINE)
# -------------------------------

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(request: AnalyzeRequest):

    url = request.url.strip()

    print(f"[ANALYZE] → {url}")

    # STEP 1 — SCRAPE
    scraped = await scrape_website(url)

    if not scraped.scrape_success:
        return AnalyzeResponse(
            success=False,
            error=f"Scraping failed: {scraped.error}",
        )

    # STEP 2 — SCORE
    try:
        scored = score_content(scraped)
    except Exception as e:
        return AnalyzeResponse(
            success=False,
            error=f"Scoring failed: {str(e)}",
        )

    # STEP 3 — CLASSIFY (AI)
    try:
        classified = classify_content(scored)
    except Exception as e:
        print("[CLASSIFIER FALLBACK]", e)
        classified = {"classified": []}

    # STEP 4 — STRUCTURE
    try:
        structured = build_structure(scored, classified)
    except Exception as e:
        return AnalyzeResponse(
            success=False,
            error=f"Structuring failed: {str(e)}",
        )

    return AnalyzeResponse(
        success=True,
        data={
            "url": url,
            "structure": structured
        }
    )


# -------------------------------
# GENERATE (FULL PRODUCT OUTPUT)
# -------------------------------

@app.post("/generate")
async def generate_endpoint(request: AnalyzeRequest):

    url = request.url.strip()

    print(f"[GENERATE] → {url}")

    # STEP 1 — SCRAPE
    scraped = await scrape_website(url)

    if not scraped.scrape_success:
        return {
            "success": False,
            "error": scraped.error,
        }

    # STEP 2 — SCORE
    try:
        scored = score_content(scraped)
    except Exception as e:
        return {"success": False, "error": f"Scoring failed: {str(e)}"}

    # STEP 3 — CLASSIFY
    try:
        classified = classify_content(scored)
    except Exception:
        classified = {"classified": []}

    # STEP 4 — STRUCTURE
    try:
        structured = build_structure(scored, classified)
    except Exception as e:
        return {"success": False, "error": f"Structuring failed: {str(e)}"}

    # STEP 5 — AI REFINEMENT (THIS IS YOUR VALUE)
    try:
        refined = refine_structure(structured)
    except Exception as e:
        print("[REFINE FALLBACK]", e)
        refined = structured

    # STEP 6 — ASSEMBLE HTML
    try:
        from assembler import assemble_website
        html = assemble_website(refined)
    except Exception as e:
        return {"success": False, "error": f"Assembly failed: {str(e)}"}

    return {
        "success": True,
        "html": html,
        "structure": refined
    }


# -------------------------------
# DEBUG (CRITICAL TOOL)
# -------------------------------

@app.post("/debug")
async def debug_pipeline(request: AnalyzeRequest):

    url = request.url.strip()

    scraped = await scrape_website(url)

    scored = score_content(scraped) if scraped.scrape_success else {}
    classified = classify_content(scored) if scored else {}
    structured = build_structure(scored, classified) if scored else {}

    try:
        refined = refine_structure(structured)
    except:
        refined = structured

    return {
        "scraped": scraped.dict() if scraped else None,
        "scored": scored,
        "classified": classified,
        "structured": structured,
        "refined": refined
    }


# -------------------------------
# ENTRYPOINT
# -------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )