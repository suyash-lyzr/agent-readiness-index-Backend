import asyncio
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from routers import analyze, survey, score, report
from state import sessions
from models.schemas import SessionStatus

load_dotenv()


def _cors_origins() -> list:
    """Local dev defaults + FRONTEND_URL (Vercel) + optional ALLOWED_ORIGINS (comma-separated)."""
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]
    front = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if front:
        origins.append(front)
    extra = os.getenv("ALLOWED_ORIGINS", "").strip()
    if extra:
        for o in extra.split(","):
            o = o.strip().rstrip("/")
            if o and o not in origins:
                origins.append(o)
    return origins


app = FastAPI(
    title="Agent Readiness Index API",
    description="AI-powered assessment of organizational AI agent readiness",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(analyze.router, prefix="/api/analyze", tags=["analyze"])
app.include_router(survey.router, prefix="/api/survey", tags=["survey"])
app.include_router(score.router, prefix="/api/score", tags=["score"])
app.include_router(report.router, prefix="/api/report", tags=["report"])


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "status": session.get("status"),
        "input_mode": session.get("input_mode"),
        "score_data": session.get("score_data"),
        "questions_to_ask": session.get("questions_to_ask", []),
        "current_question_index": session.get("current_question_index", 0),
        "extracted_signals": session.get("extracted_signals"),
        "survey_answers": session.get("survey_answers", {}),
        "error": session.get("error"),
        "thinking_steps": session.get("thinking_steps", []),
    }


@app.get("/api/stream/{session_id}")
async def stream_thinking(session_id: str):
    """SSE endpoint streaming agent thinking steps in real-time."""

    async def event_generator():
        session = sessions.get(session_id)
        if not session:
            yield f"data: {json.dumps({'step': 'error', 'message': 'Session not found', 'status': 'error'})}\n\n"
            return

        sent_count = 0
        max_polls = 120  # 2 minutes max
        poll_count = 0

        while poll_count < max_polls:
            session = sessions.get(session_id)
            if not session:
                break

            steps = session.get("thinking_steps", [])

            # Send any new steps
            while sent_count < len(steps):
                step = steps[sent_count]
                yield f"data: {json.dumps(step)}\n\n"
                sent_count += 1

            status = session.get("status")

            # If terminal state, send final event and close
            if status in (SessionStatus.complete, SessionStatus.error):
                if status == SessionStatus.complete:
                    yield f"data: {json.dumps({'step': 'complete', 'message': 'Analysis complete! Redirecting to results...', 'status': 'complete'})}\n\n"
                else:
                    error_msg = session.get("error", "Unknown error")
                    yield f"data: {json.dumps({'step': 'error', 'message': f'Error: {error_msg}', 'status': 'error'})}\n\n"
                yield "data: [DONE]\n\n"
                break

            # If waiting for survey, stop streaming
            if status == SessionStatus.awaiting_survey and sent_count >= len(steps):
                yield f"data: {json.dumps({'step': 'ready', 'message': 'Ready for survey questions.', 'status': 'complete'})}\n\n"
                yield "data: [DONE]\n\n"
                break

            await asyncio.sleep(0.5)
            poll_count += 1

        if poll_count >= max_polls:
            yield f"data: {json.dumps({'step': 'timeout', 'message': 'Stream timeout', 'status': 'error'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "message": "Agent Readiness Index API",
        "docs": "/docs",
        "health": "/health",
    }
