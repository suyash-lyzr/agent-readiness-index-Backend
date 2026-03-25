import anthropic
import json
import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

EXTRACTION_MODEL = "claude-sonnet-4-6"
SCORING_MODEL = "claude-opus-4-6"

SURVEY_QUESTIONS_BANK = {
    "BG1": {
        "id": "BG1",
        "pillar": "About Your Company",
        "question": "What industry or sector does your company operate in?",
        "options": [
            "Technology / SaaS",
            "Financial Services / Banking / Insurance",
            "Healthcare / Life Sciences",
            "Retail / E-commerce",
            "Manufacturing / Logistics",
            "Professional Services / Consulting",
            "Education",
            "Other",
        ],
    },
    "BG2": {
        "id": "BG2",
        "pillar": "About Your Company",
        "question": "How large is your organization?",
        "options": [
            "1–50 employees (Startup / Small business)",
            "51–200 employees (Growing company)",
            "201–1,000 employees (Mid-market)",
            "1,001–10,000 employees (Enterprise)",
            "10,000+ employees (Large enterprise)",
        ],
    },
    "D1": {
        "id": "D1",
        "pillar": "Your Data",
        "question": "How is your business data primarily stored?",
        "options": [
            "Spreadsheets / shared drives",
            "CRM / ERP systems (e.g., Salesforce, SAP)",
            "Custom databases",
            "A mix of the above",
            "Not sure",
        ],
    },
    "D2": {
        "id": "D2",
        "pillar": "Your Data",
        "question": "Can your teams access business data through APIs or integrations?",
        "options": ["Yes, easily and extensively", "Partially – some systems are connected", "No, mostly manual access", "Not sure"],
    },
    "D3": {
        "id": "D3",
        "pillar": "Your Data",
        "question": "Do you have documented knowledge bases, SOPs, or internal wikis?",
        "options": ["Yes, comprehensive and up-to-date", "Partial – some documentation exists", "No formal documentation"],
    },
    "P1": {
        "id": "P1",
        "pillar": "Your Workflows",
        "question": "What percentage of daily operations involve repetitive, rule-based tasks?",
        "options": ["Less than 20%", "20–40%", "40–60%", "60% or more"],
    },
    "P2": {
        "id": "P2",
        "pillar": "Your Workflows",
        "question": "How well documented are your business processes?",
        "options": [
            "Detailed SOPs exist for most processes",
            "High-level only – broad steps documented",
            "Tribal knowledge – in people's heads",
            "No documentation at all",
        ],
    },
    "T1": {
        "id": "T1",
        "pillar": "Your Technology",
        "question": "How would you describe your current technology stack?",
        "options": [
            "Modern and cloud-native (AWS, GCP, Azure, SaaS-first)",
            "A mix of cloud and on-premise",
            "Mostly legacy / on-premise systems",
            "Not sure",
        ],
    },
    "T2": {
        "id": "T2",
        "pillar": "Your Technology",
        "question": "Do you currently use any automation or workflow tools?",
        "options": ["Yes, extensively (e.g., Zapier, Make, RPA, CI/CD)", "Some tools in certain departments", "No automation tools in use", "Planning to adopt soon"],
    },
    "C1": {
        "id": "C1",
        "pillar": "Your Team",
        "question": "How would you describe leadership's attitude toward AI adoption?",
        "options": ["Active champion – pushing for AI initiatives", "Supportive – open and interested", "Cautious – waiting to see", "Resistant – skeptical of AI", "Not discussed at leadership level"],
    },
    "C2": {
        "id": "C2",
        "pillar": "Your Team",
        "question": "What is your team's current AI literacy level?",
        "options": [
            "High – many already using AI tools daily",
            "Medium – some exposure and experimentation",
            "Low – little to no hands-on experience",
        ],
    },
    "U1": {
        "id": "U1",
        "pillar": "Your AI Goals",
        "question": "Have you identified specific problems you want AI agents to solve?",
        "options": ["Yes, clearly defined use cases with requirements", "We have vague ideas but nothing concrete", "No specific use cases identified yet", "Just exploring what's possible"],
    },
    "U2": {
        "id": "U2",
        "pillar": "Your AI Goals",
        "question": "What's your primary motivation for exploring AI agents?",
        "options": ["Cut operational costs", "Scale without adding headcount", "Improve customer experience", "Competitive pressure / FOMO", "Genuine curiosity / innovation"],
    },
    "G1": {
        "id": "G1",
        "pillar": "Security & Compliance",
        "question": "Does your industry have specific data privacy or regulatory requirements?",
        "options": ["Yes – heavily regulated (GDPR, HIPAA, SOC2, PCI-DSS, etc.)", "Some light-touch regulations", "No specific regulations apply", "Not sure"],
    },
    "G2": {
        "id": "G2",
        "pillar": "Security & Compliance",
        "question": "Do you have data security and privacy policies in place?",
        "options": ["Formal, documented policies in place", "Informal practices but nothing written", "No policies currently", "Working on establishing them"],
    },
}

EXTRACTION_SYSTEM_PROMPT = """You are an expert AI readiness analyst. Your job is to extract signals from company content (website text or document) to assess how ready they are for AI agent adoption across 6 key pillars.

Be thorough and analytical. Look for explicit and implicit signals about:
- Industry and vertical
- Company size and scale
- Technology stack and maturity
- AI/automation mentions
- Data infrastructure signals
- Process maturity signals
- Team culture and leadership signals
- Compliance/regulatory environment

CRITICAL OUTPUT FORMAT:
1. First, write exactly 4 short thinking steps. Each MUST start with "THOUGHT: " on its own line.
   Keep each thought under 12 words. First person, present tense. Examples:
   THOUGHT: Reading the content to identify the industry and company type.
   THOUGHT: Found mentions of cloud infrastructure and SaaS tools.
   THOUGHT: Data and compliance signals are unclear from the content.
   THOUGHT: Selecting targeted questions to fill the gaps I found.
2. Then output the JSON block, starting with { on a new line. No markdown fences.
   No other text before or after the JSON."""

EXTRACTION_USER_PROMPT = """Analyze the following content from a company and extract AI agent readiness signals.

CONTENT:
{content}

Return a JSON object with this exact structure:
{{
  "extracted_signals": {{
    "industry": "specific industry/vertical",
    "company_size": "startup/SMB/mid-market/enterprise or employee count if mentioned",
    "digital_maturity": "high/medium/low",
    "ai_mentions": ["list of specific AI/ML/automation mentions found"],
    "tech_mentions": ["list of specific technologies, tools, platforms mentioned"],
    "geography": "country/region if determinable",
    "compliance_flags": ["list of regulatory/compliance signals found"]
  }},
  "pillar_confidence": {{
    "data_readiness": "high/medium/low/unknown",
    "process_readiness": "high/medium/low/unknown",
    "tech_infrastructure": "high/medium/low/unknown",
    "people_culture": "high/medium/low/unknown",
    "use_case_clarity": "high/medium/low/unknown",
    "governance_compliance": "high/medium/low/unknown"
  }},
  "questions_to_ask": ["D1", "P1", "T1"],
  "reasoning": "2-3 sentences explaining what you found and what's missing"
}}

For questions_to_ask: include question IDs from this list ONLY for pillars where confidence is low or unknown. If confidence is high or medium for a pillar, skip those questions. Aim for 5-8 questions maximum.

Available question IDs:
- BG1 (industry/sector), BG2 (company size) — include these if industry or company_size is "unknown" or vague in extracted signals
- D1, D2, D3 (data readiness)
- P1, P2 (workflows/processes)
- T1, T2 (technology)
- C1, C2 (people/culture)
- U1, U2 (AI goals/use cases)
- G1, G2 (governance/compliance)

Always place BG1 and BG2 first in the list if included."""

SCORING_SYSTEM_PROMPT = """You are a senior AI readiness consultant performing a structured assessment. You have access to signals extracted from a company's website or documents, plus their survey responses. Your job is to score the company across 6 pillars and generate a comprehensive, honest assessment.

Scoring guidelines:
- Be honest and calibrated – don't inflate scores
- Base scores on concrete evidence, not assumptions
- 0-25: Very early stage, significant gaps
- 26-50: Some foundations but major gaps remain
- 51-75: Good foundation with specific areas to improve
- 76-100: Strong readiness, minor gaps only

CRITICAL OUTPUT RULES — keep all text extremely concise:
- "reasoning": ONE sentence max (15 words). Example: "Strong API infrastructure but data documentation is incomplete."
- "evidence": each item max 10 words. Example: "Cloud-native SaaS platform on AWS"
- "gaps": each item max 10 words. Example: "No formal AI governance framework in place"
- "top_strengths": each item max 12 words, punchy. Example: "100+ agent blueprints across six enterprise verticals"
- "critical_gaps": each item max 12 words, punchy. Example: "Internal data systems lack API access and documentation"
- DO NOT write paragraphs. Every field must be a short, scannable phrase.

You MUST return valid JSON only. No markdown, no explanation outside the JSON."""

SCORING_USER_PROMPT = """Score this company's AI agent readiness based on all available data.

EXTRACTED SIGNALS FROM CONTENT:
{extracted_signals}

PILLAR CONFIDENCE LEVELS:
{pillar_confidence}

SURVEY ANSWERS:
{survey_answers}

INPUT MODE: {input_mode}

Return a JSON object with this exact structure:
{{
  "overall_score": <number 0-100>,
  "tier": "<AI Exploring|AI Experimenting|AI Scaling|AI Native>",
  "pillar_scores": {{
    "use_case_clarity": {{
      "score": <0-100>,
      "weight": 0.20,
      "weighted_score": <score * 0.20>,
      "reasoning": "detailed reasoning for this score",
      "evidence": ["specific evidence points"],
      "gaps": ["specific gaps identified"]
    }},
    "data_readiness": {{
      "score": <0-100>,
      "weight": 0.20,
      "weighted_score": <score * 0.20>,
      "reasoning": "detailed reasoning for this score",
      "evidence": ["specific evidence points"],
      "gaps": ["specific gaps identified"]
    }},
    "process_readiness": {{
      "score": <0-100>,
      "weight": 0.20,
      "weighted_score": <score * 0.20>,
      "reasoning": "detailed reasoning for this score",
      "evidence": ["specific evidence points"],
      "gaps": ["specific gaps identified"]
    }},
    "tech_infrastructure": {{
      "score": <0-100>,
      "weight": 0.15,
      "weighted_score": <score * 0.15>,
      "reasoning": "detailed reasoning for this score",
      "evidence": ["specific evidence points"],
      "gaps": ["specific gaps identified"]
    }},
    "people_culture": {{
      "score": <0-100>,
      "weight": 0.15,
      "weighted_score": <score * 0.15>,
      "reasoning": "detailed reasoning for this score",
      "evidence": ["specific evidence points"],
      "gaps": ["specific gaps identified"]
    }},
    "governance_compliance": {{
      "score": <0-100>,
      "weight": 0.10,
      "weighted_score": <score * 0.10>,
      "reasoning": "detailed reasoning for this score",
      "evidence": ["specific evidence points"],
      "gaps": ["specific gaps identified"]
    }}
  }},
  "top_strengths": ["3-4 specific strengths"],
  "critical_gaps": ["3-4 specific critical gaps that must be addressed"],
  "transparency": {{
    "extracted_from_url": ["list of signals extracted from URL/content"],
    "extracted_from_pdf": [],
    "inferred": ["list of reasonable inferences made"],
    "from_survey": ["list of facts learned from survey answers"],
    "questions_skipped": ["questions not asked and why"]
  }}
}}

The overall_score should equal the sum of all weighted_scores. Tier mapping: 0-25=AI Exploring, 26-50=AI Experimenting, 51-75=AI Scaling, 76-100=AI Native."""


def get_async_client() -> anthropic.AsyncAnthropic:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in environment")
    return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


def _parse_json(text: str) -> Dict[str, Any]:
    """Parse JSON from Claude response, with regex fallback."""
    import re
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from Claude response: {text[:500]}")


async def extract_signals(content: str, on_thought_callback=None) -> Dict[str, Any]:
    """Use claude-sonnet-4-6 to extract readiness signals from content."""
    client = get_async_client()
    prompt = EXTRACTION_USER_PROMPT.format(content=content[:10000])

    if on_thought_callback:
        accumulated = ""
        json_started = False
        line_buffer = ""
        emitted_thoughts: set = set()

        async with client.messages.stream(
            model=EXTRACTION_MODEL,
            max_tokens=2500,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for chunk in stream.text_stream:
                accumulated += chunk
                if not json_started:
                    line_buffer += chunk
                    # Emit complete THOUGHT: lines as they arrive
                    while "\n" in line_buffer:
                        line, line_buffer = line_buffer.split("\n", 1)
                        line = line.strip()
                        if line.startswith("THOUGHT:"):
                            thought = line[len("THOUGHT:"):].strip()
                            if thought and thought not in emitted_thoughts:
                                emitted_thoughts.add(thought)
                                await on_thought_callback(thought)
                    # Detect start of JSON
                    if "{" in accumulated:
                        json_started = True

        # Extract the JSON portion
        if "{" in accumulated:
            json_str = accumulated[accumulated.index("{"):]
        else:
            json_str = accumulated
        return _parse_json(json_str.strip())

    else:
        message = await client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2500,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        json_str = raw[raw.index("{"):] if "{" in raw else raw
        return _parse_json(json_str)


async def score_readiness(
    extracted_signals: Dict[str, Any],
    pillar_confidence: Dict[str, str],
    survey_answers: Dict[str, str],
    input_mode: str,
) -> Dict[str, Any]:
    """Use claude-opus-4-6 to score readiness and generate full assessment."""
    client = get_async_client()

    survey_formatted = "\n".join(
        [f"  {qid}: {answer}" for qid, answer in survey_answers.items()]
    ) or "  No survey answers provided"

    prompt = SCORING_USER_PROMPT.format(
        extracted_signals=json.dumps(extracted_signals, indent=2),
        pillar_confidence=json.dumps(pillar_confidence, indent=2),
        survey_answers=survey_formatted,
        input_mode=input_mode,
    )

    try:
        message = await client.messages.create(
            model=SCORING_MODEL,
            max_tokens=4000,
            system=SCORING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError:
        # Fallback to sonnet
        message = await client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=4000,
            system=SCORING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

    return _parse_json(message.content[0].text.strip())


def get_survey_question(question_id: str) -> Optional[Dict[str, Any]]:
    """Get survey question by ID."""
    return SURVEY_QUESTIONS_BANK.get(question_id)


def get_questions_for_survey_only() -> list:
    """Return all question IDs for survey-only mode."""
    return list(SURVEY_QUESTIONS_BANK.keys())


def get_default_signals_for_survey() -> Dict[str, Any]:
    """Return empty signals structure for survey-only mode."""
    return {
        "extracted_signals": {
            "industry": "unknown",
            "company_size": "unknown",
            "digital_maturity": "unknown",
            "ai_mentions": [],
            "tech_mentions": [],
            "geography": "unknown",
            "compliance_flags": [],
        },
        "pillar_confidence": {
            "data_readiness": "unknown",
            "process_readiness": "unknown",
            "tech_infrastructure": "unknown",
            "people_culture": "unknown",
            "use_case_clarity": "unknown",
            "governance_compliance": "unknown",
        },
        "questions_to_ask": get_questions_for_survey_only(),
        "reasoning": "Survey-only mode – no external content provided. Asking all questions.",
    }
