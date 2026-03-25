from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from models.schemas import SessionStatus
from services.claude_service import score_readiness
from services.scorer import get_tier, calculate_overall_score
from state import sessions

router = APIRouter()


async def run_scoring(session_id: str):
    """Background task: run final scoring via Claude."""
    session = sessions.get(session_id)
    if not session:
        return

    try:
        session["status"] = SessionStatus.scoring
        session["thinking_steps"].append(
            {
                "step": "scoring",
                "message": "Synthesizing all signals and survey answers for final scoring...",
                "status": "in_progress",
            }
        )

        extracted_signals = session.get("extracted_signals") or {}
        pillar_confidence = session.get("pillar_confidence") or {}
        survey_answers = session.get("survey_answers") or {}
        input_mode = str(session.get("input_mode", "survey"))

        score_data = await score_readiness(
            extracted_signals=extracted_signals,
            pillar_confidence=pillar_confidence,
            survey_answers=survey_answers,
            input_mode=input_mode,
        )

        session["score_data"] = score_data
        session["status"] = SessionStatus.complete

        session["thinking_steps"].append(
            {
                "step": "scoring",
                "message": f"Scoring complete. Overall score: {score_data.get('overall_score', 0):.0f}/100 — {score_data.get('tier', 'Unknown')}",
                "status": "complete",
                "score": score_data.get("overall_score", 0),
                "tier": score_data.get("tier", ""),
            }
        )

    except Exception as e:
        session["status"] = SessionStatus.error
        session["error"] = str(e)
        session["thinking_steps"].append(
            {
                "step": "scoring",
                "message": f"Scoring failed: {str(e)}",
                "status": "error",
            }
        )


@router.post("/{session_id}")
async def trigger_scoring(session_id: str, background_tasks: BackgroundTasks):
    """Trigger final scoring for a session."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == SessionStatus.error:
        raise HTTPException(status_code=400, detail=f"Session in error state: {session.get('error')}")

    if session["status"] == SessionStatus.complete:
        return {"message": "Already scored", "score_data": session["score_data"]}

    if session["status"] == SessionStatus.scoring:
        return {"message": "Scoring in progress"}

    if session["status"] not in (SessionStatus.awaiting_survey,):
        raise HTTPException(
            status_code=400,
            detail=f"Session not ready for scoring. Status: {session['status']}. Complete the survey first.",
        )

    background_tasks.add_task(run_scoring, session_id)
    return {"message": "Scoring started", "session_id": session_id}
