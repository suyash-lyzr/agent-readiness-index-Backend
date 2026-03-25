from typing import Dict, Any


PILLAR_CONFIG = {
    "use_case_clarity": {
        "weight": 0.20,
        "label": "AI Use Cases",
        "description": "Do you know what problems AI agents should solve?",
        "weight_reasoning": (
            "Use case clarity is the single most critical factor. Without knowing what "
            "problem to solve, even perfect infrastructure is useless. It drives 20% "
            "because clarity of purpose determines project success."
        ),
    },
    "data_readiness": {
        "weight": 0.20,
        "label": "Data & Access",
        "description": "Is your business data organized, connected, and accessible?",
        "weight_reasoning": (
            "AI agents are only as good as the data they operate on. Structured, "
            "accessible data via APIs is a hard prerequisite for most agent workflows. "
            "Equally weighted with use case clarity at 20%."
        ),
    },
    "process_readiness": {
        "weight": 0.20,
        "label": "Workflows",
        "description": "Are your business processes documented and repeatable?",
        "weight_reasoning": (
            "Agents automate processes. If processes are undocumented or inconsistent, "
            "agents can't reliably follow them. 20% weight reflects that process maturity "
            "directly limits what agents can do."
        ),
    },
    "tech_infrastructure": {
        "weight": 0.15,
        "label": "Technology",
        "description": "Is your tech stack modern, cloud-connected, and API-ready?",
        "weight_reasoning": (
            "Modern cloud-native infrastructure dramatically lowers the cost and complexity "
            "of agent deployment. At 15%, it's highly important but slightly secondary to "
            "use case, data, and process readiness."
        ),
    },
    "people_culture": {
        "weight": 0.15,
        "label": "Team Readiness",
        "description": "Is your leadership and team ready to adopt AI?",
        "weight_reasoning": (
            "Even the best technology fails without human adoption. Leadership buy-in and "
            "team literacy determine rollout success. 15% weight acknowledges this is "
            "often the silent killer of AI initiatives."
        ),
    },
    "governance_compliance": {
        "weight": 0.10,
        "label": "Security & Compliance",
        "description": "Do you have data privacy and security policies in place?",
        "weight_reasoning": (
            "Governance matters, especially in regulated industries, but it's the most "
            "addressable gap – policies can be created relatively quickly. At 10%, it's "
            "important but doesn't block initial AI readiness like data or process gaps do."
        ),
    },
}


def get_tier(score: float) -> str:
    if score <= 25:
        return "AI Exploring"
    elif score <= 50:
        return "AI Experimenting"
    elif score <= 75:
        return "AI Scaling"
    else:
        return "AI Native"


def get_tier_description(tier: str) -> str:
    descriptions = {
        "AI Exploring": (
            "Your organization is at the very beginning of the AI readiness journey. "
            "Significant foundational work is needed before agent deployment will be "
            "viable. Focus on data infrastructure, process documentation, and building "
            "internal AI awareness."
        ),
        "AI Experimenting": (
            "You have some foundations in place but key gaps remain. You can run "
            "limited AI pilots in specific areas, but broader deployment requires "
            "addressing data access, process maturity, or organizational alignment. "
            "Pick one high-impact use case to prove value."
        ),
        "AI Scaling": (
            "Strong readiness across most dimensions. You have the infrastructure, "
            "data, and organizational alignment to deploy AI agents at scale. Focus "
            "on filling specific gaps identified and establishing governance frameworks "
            "as you expand."
        ),
        "AI Native": (
            "Exceptional AI readiness. Your organization has the maturity, infrastructure, "
            "and culture to operate as a truly AI-native business. Focus on advanced "
            "multi-agent architectures and maintaining your competitive edge."
        ),
    }
    return descriptions.get(tier, "")


def get_pillar_config() -> Dict[str, Any]:
    return PILLAR_CONFIG


def calculate_overall_score(pillar_scores: Dict[str, Any]) -> float:
    """Calculate overall score from pillar scores and weights."""
    total = 0.0
    for pillar_key, config in PILLAR_CONFIG.items():
        if pillar_key in pillar_scores:
            score = pillar_scores[pillar_key].get("score", 0)
            total += score * config["weight"]
    return round(total, 1)
