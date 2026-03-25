from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models.schemas import SessionStatus
from services.report_generator import generate_pdf_report
from state import sessions

router = APIRouter()


@router.get("/{session_id}")
async def download_report(session_id: str):
    """Generate and return a PDF report for a completed session."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] != SessionStatus.complete:
        raise HTTPException(
            status_code=400,
            detail=f"Report not available yet. Session status: {session['status']}",
        )

    score_data = session.get("score_data")
    if not score_data:
        raise HTTPException(status_code=404, detail="No score data found for this session")

    try:
        pdf_bytes = generate_pdf_report(session_id, score_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="agent-readiness-report-{session_id[:8]}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
