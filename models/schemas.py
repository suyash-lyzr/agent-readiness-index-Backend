from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class InputMode(str, Enum):
    url = "url"
    pdf = "pdf"
    survey = "survey"


class SessionStatus(str, Enum):
    created = "created"
    extracting = "extracting"
    awaiting_survey = "awaiting_survey"
    scoring = "scoring"
    complete = "complete"
    error = "error"


class SurveyQuestion(BaseModel):
    id: str
    pillar: str
    question: str
    options: List[str]


class ExtractedSignals(BaseModel):
    industry: Optional[str] = None
    company_size: Optional[str] = None
    digital_maturity: Optional[str] = None
    ai_mentions: List[str] = []
    tech_mentions: List[str] = []
    geography: Optional[str] = None
    compliance_flags: List[str] = []


class PillarScore(BaseModel):
    score: float
    weight: float
    weighted_score: float
    reasoning: str
    evidence: List[str] = []
    gaps: List[str] = []


class Transparency(BaseModel):
    extracted_from_url: List[str] = []
    extracted_from_pdf: List[str] = []
    inferred: List[str] = []
    from_survey: List[str] = []
    questions_skipped: List[str] = []


class ScoreData(BaseModel):
    overall_score: float
    tier: str
    pillar_scores: Dict[str, PillarScore]
    top_strengths: List[str] = []
    critical_gaps: List[str] = []
    transparency: Transparency


class SessionState(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.created
    input_mode: Optional[InputMode] = None
    raw_content: Optional[str] = None
    extracted_signals: Optional[Dict[str, Any]] = None
    pillar_confidence: Optional[Dict[str, str]] = None
    questions_to_ask: List[str] = []
    survey_answers: Dict[str, str] = {}
    current_question_index: int = 0
    score_data: Optional[Dict[str, Any]] = None
    thinking_steps: List[Dict[str, Any]] = []
    error: Optional[str] = None


class AnalyzeUrlRequest(BaseModel):
    url: str


class SurveyStartRequest(BaseModel):
    pass


class SurveyAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str


class SessionResponse(BaseModel):
    session_id: str
    status: str
    score_data: Optional[Dict[str, Any]] = None
    questions_to_ask: List[str] = []
    current_question_index: int = 0
    extracted_signals: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
