import uuid
import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from typing import Dict, Any

from models.schemas import AnalyzeUrlRequest, SessionStatus, InputMode
from services.url_scraper import scrape_url, crawl_website, is_valid_url
from services.pdf_parser import parse_pdf
from services.claude_service import extract_signals, get_default_signals_for_survey
from state import sessions

router = APIRouter()


async def run_extraction(session_id: str, content: str, input_mode: str):
    """Background task: extract signals and update session state."""
    session = sessions.get(session_id)
    if not session:
        return

    try:
        word_count = len(content.split())
        session["thinking_steps"].append({
            "step": "extraction_start",
            "message": f"Got {word_count:,} words of content. Starting analysis...",
            "status": "complete",
        })

        thought_count = [0]

        async def handle_thought(thought: str):
            if session:
                thought_count[0] += 1
                session["thinking_steps"].append({
                    "step": "extraction_thought",
                    "message": thought,
                    "status": "complete",
                })

        result = await extract_signals(content, on_thought_callback=handle_thought)

        extracted = result.get("extracted_signals", {})
        confidence = result.get("pillar_confidence", {})
        questions = result.get("questions_to_ask", [])
        reasoning = result.get("reasoning", "")

        session["extracted_signals"] = extracted
        session["pillar_confidence"] = confidence
        session["questions_to_ask"] = questions
        session["raw_content"] = content

        # Build structured signal data for visual display
        signals_data = {}
        if extracted.get("industry"):
            signals_data["Industry"] = extracted["industry"]
        if extracted.get("company_size"):
            signals_data["Company Size"] = extracted["company_size"]
        if extracted.get("digital_maturity"):
            signals_data["Digital Maturity"] = extracted["digital_maturity"]
        if extracted.get("ai_mentions"):
            signals_data["AI Mentions"] = extracted["ai_mentions"][:4]
        if extracted.get("tech_mentions"):
            signals_data["Tech Stack"] = extracted["tech_mentions"][:5]
        if extracted.get("compliance_flags"):
            signals_data["Compliance"] = extracted["compliance_flags"][:3]

        session["thinking_steps"].append(
            {
                "step": "extraction",
                "message": f"Extracted {len(signals_data)} signal categories from content",
                "status": "complete",
                "signals": signals_data,
            }
        )

        # Friendly pillar name mapping for user-facing messages
        pillar_friendly = {
            "data_readiness": "data & systems",
            "process_readiness": "workflows",
            "tech_infrastructure": "technology",
            "people_culture": "team readiness",
            "use_case_clarity": "AI goals",
            "governance_compliance": "security & compliance",
        }

        unknown_pillars = [k for k, v in confidence.items() if v in ("low", "unknown")]
        if unknown_pillars:
            friendly_gaps = [pillar_friendly.get(p, p.replace("_", " ")) for p in unknown_pillars]
            session["thinking_steps"].append(
                {
                    "step": "gap_analysis",
                    "message": f"Need more info about: {', '.join(friendly_gaps)}",
                    "status": "complete",
                }
            )
        else:
            session["thinking_steps"].append(
                {
                    "step": "gap_analysis",
                    "message": "Good coverage from content — minimal questions needed.",
                    "status": "complete",
                }
            )

        # Build readable question summary (e.g. "3 about data, 2 about compliance")
        qid_to_category = {
            "BG1": "company background", "BG2": "company background",
            "D1": "data", "D2": "data", "D3": "data",
            "P1": "workflows", "P2": "workflows",
            "T1": "technology", "T2": "technology",
            "C1": "team", "C2": "team",
            "U1": "AI goals", "U2": "AI goals",
            "G1": "compliance", "G2": "compliance",
        }
        category_counts: dict = {}
        for qid in questions:
            cat = qid_to_category.get(qid, "general")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        question_summary = ", ".join(f"{count} about {cat}" for cat, count in category_counts.items())

        session["thinking_steps"].append(
            {
                "step": "questions",
                "message": f"Prepared {len(questions)} targeted questions: {question_summary}" if question_summary else f"Prepared {len(questions)} targeted questions",
                "status": "complete",
            }
        )

        session["status"] = SessionStatus.awaiting_survey

    except Exception as e:
        session["status"] = SessionStatus.error
        session["error"] = str(e)
        session["thinking_steps"].append(
            {
                "step": "extraction",
                "message": f"Error during extraction: {str(e)}",
                "status": "error",
            }
        )


@router.post("/url")
async def analyze_url(request: AnalyzeUrlRequest, background_tasks: BackgroundTasks):
    """Accept a URL, scrape it, and begin async extraction."""
    if not is_valid_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid URL format. Please include http:// or https://")

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "session_id": session_id,
        "status": SessionStatus.extracting,
        "input_mode": InputMode.url,
        "raw_content": None,
        "extracted_signals": None,
        "pillar_confidence": None,
        "questions_to_ask": [],
        "survey_answers": {},
        "current_question_index": 0,
        "score_data": None,
        "thinking_steps": [
            {
                "step": "scraping",
                "message": f"Crawling {request.url} and discovering internal pages...",
                "status": "in_progress",
            }
        ],
        "error": None,
    }

    def on_page_crawled(page_url: str, count: int, total: int):
        parsed_path = page_url.split("//", 1)[-1].split("/", 1)
        short = "/" + parsed_path[1] if len(parsed_path) > 1 and parsed_path[1] else "/"
        if count == 1:
            sessions[session_id]["thinking_steps"][0]["status"] = "complete"
            sessions[session_id]["thinking_steps"][0]["message"] = f"Crawled homepage — found internal pages to scan"
        else:
            sessions[session_id]["thinking_steps"].append({
                "step": f"crawl_page_{count}",
                "message": f"Crawled page {count}: {short}",
                "status": "complete",
            })

    try:
        content = crawl_website(request.url, max_pages=10, on_page_callback=on_page_crawled)
        page_count = content.count("--- PAGE ")
        word_count = len(content.split())
        sessions[session_id]["thinking_steps"].append({
            "step": "crawl_complete",
            "message": f"Crawled {page_count} pages — {word_count:,} words of content collected",
            "status": "complete",
        })
    except Exception as e:
        sessions[session_id]["status"] = SessionStatus.error
        sessions[session_id]["error"] = str(e)
        sessions[session_id]["thinking_steps"][0]["status"] = "error"
        sessions[session_id]["thinking_steps"][0]["message"] = f"Failed to crawl website: {str(e)}"
        return {"session_id": session_id}

    background_tasks.add_task(run_extraction, session_id, content, "url")
    return {"session_id": session_id}


@router.post("/pdf")
async def analyze_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Accept a PDF upload, parse it, and begin async extraction."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="PDF file too large. Maximum 10MB.")

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "session_id": session_id,
        "status": SessionStatus.extracting,
        "input_mode": InputMode.pdf,
        "raw_content": None,
        "extracted_signals": None,
        "pillar_confidence": None,
        "questions_to_ask": [],
        "survey_answers": {},
        "current_question_index": 0,
        "score_data": None,
        "thinking_steps": [
            {
                "step": "parsing",
                "message": f"Parsing PDF: {file.filename}...",
                "status": "in_progress",
            }
        ],
        "error": None,
    }

    try:
        content = parse_pdf(file_bytes)
        sessions[session_id]["thinking_steps"][0]["status"] = "complete"
        sessions[session_id]["thinking_steps"][0]["message"] = f"Successfully parsed {len(content)} characters from PDF"
    except Exception as e:
        sessions[session_id]["status"] = SessionStatus.error
        sessions[session_id]["error"] = str(e)
        sessions[session_id]["thinking_steps"][0]["status"] = "error"
        sessions[session_id]["thinking_steps"][0]["message"] = f"Failed to parse PDF: {str(e)}"
        return {"session_id": session_id}

    background_tasks.add_task(run_extraction, session_id, content, "pdf")
    return {"session_id": session_id}
