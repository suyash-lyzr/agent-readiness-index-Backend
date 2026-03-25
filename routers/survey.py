import uuid
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any

from models.schemas import SurveyAnswerRequest, SessionStatus, InputMode
from services.claude_service import get_survey_question, get_default_signals_for_survey
from state import sessions

router = APIRouter()


@router.post("/start")
async def start_survey():
    """Start a survey-only session (no URL or PDF)."""
    session_id = str(uuid.uuid4())
    defaults = get_default_signals_for_survey()

    sessions[session_id] = {
        "session_id": session_id,
        "status": SessionStatus.awaiting_survey,
        "input_mode": InputMode.survey,
        "raw_content": None,
        "extracted_signals": defaults["extracted_signals"],
        "pillar_confidence": defaults["pillar_confidence"],
        "questions_to_ask": defaults["questions_to_ask"],
        "survey_answers": {},
        "current_question_index": 0,
        "score_data": None,
        "thinking_steps": [
            {
                "step": "survey_start",
                "message": "Survey-only mode. I'll ask you all relevant questions to assess your AI readiness.",
                "status": "complete",
            }
        ],
        "error": None,
    }

    # Return first question
    first_q_id = defaults["questions_to_ask"][0] if defaults["questions_to_ask"] else None
    first_question = get_survey_question(first_q_id) if first_q_id else None

    return {
        "session_id": session_id,
        "first_question": first_question,
        "total_questions": len(defaults["questions_to_ask"]),
    }


@router.post("/answer")
async def submit_answer(request: SurveyAnswerRequest):
    """Submit an answer to a survey question and get the next question."""
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == SessionStatus.error:
        raise HTTPException(status_code=400, detail=f"Session in error state: {session.get('error')}")

    if session["status"] not in (SessionStatus.awaiting_survey,):
        raise HTTPException(
            status_code=400,
            detail=f"Session not in survey state. Current status: {session['status']}",
        )

    # Record the answer
    session["survey_answers"][request.question_id] = request.answer

    # Find next question
    questions_to_ask = session.get("questions_to_ask", [])
    current_idx = session.get("current_question_index", 0)

    # Find the index of the question just answered
    try:
        answered_idx = questions_to_ask.index(request.question_id)
        next_idx = answered_idx + 1
    except ValueError:
        next_idx = current_idx + 1

    session["current_question_index"] = next_idx

    if next_idx < len(questions_to_ask):
        next_q_id = questions_to_ask[next_idx]
        next_question = get_survey_question(next_q_id)
        return {
            "next_question": next_question,
            "progress": {
                "current": next_idx + 1,
                "total": len(questions_to_ask),
                "answered": len(session["survey_answers"]),
            },
            "survey_complete": False,
        }
    else:
        # Survey complete
        return {
            "next_question": None,
            "progress": {
                "current": len(questions_to_ask),
                "total": len(questions_to_ask),
                "answered": len(session["survey_answers"]),
            },
            "survey_complete": True,
        }


@router.get("/questions/{session_id}")
async def get_questions(session_id: str):
    """Get all questions for a session."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    questions_to_ask = session.get("questions_to_ask", [])
    questions = []
    for q_id in questions_to_ask:
        q = get_survey_question(q_id)
        if q:
            questions.append(q)

    return {
        "questions": questions,
        "total": len(questions),
        "answers": session.get("survey_answers", {}),
    }
