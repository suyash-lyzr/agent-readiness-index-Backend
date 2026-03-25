from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics import renderPDF
import io
from typing import Dict, Any
from services.scorer import PILLAR_CONFIG, get_tier_description


NAVY = colors.HexColor("#0f172a")
DARK_BLUE = colors.HexColor("#1e3a5f")
LIGHT_BLUE = colors.HexColor("#3b82f6")
CYAN = colors.HexColor("#06b6d4")
GREEN = colors.HexColor("#10b981")
ORANGE = colors.HexColor("#f59e0b")
RED = colors.HexColor("#ef4444")
GRAY = colors.HexColor("#64748b")
LIGHT_GRAY = colors.HexColor("#f1f5f9")
WHITE = colors.white


def get_score_color(score: float):
    if score >= 75:
        return GREEN
    elif score >= 50:
        return LIGHT_BLUE
    elif score >= 25:
        return ORANGE
    else:
        return RED


def generate_pdf_report(session_id: str, score_data: Dict[str, Any]) -> bytes:
    """Generate a professional PDF report for the Agent Readiness assessment."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=WHITE,
        spaceAfter=6,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#94a3b8"),
        spaceAfter=4,
        fontName="Helvetica",
        alignment=TA_CENTER,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=NAVY,
        spaceBefore=16,
        spaceAfter=8,
        fontName="Helvetica-Bold",
        borderPad=4,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4,
        fontName="Helvetica",
        leading=14,
    )
    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#334155"),
        spaceAfter=3,
        fontName="Helvetica",
        leftIndent=16,
        bulletIndent=6,
        leading=14,
    )
    pillar_title_style = ParagraphStyle(
        "PillarTitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=NAVY,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "SmallText",
        parent=styles["Normal"],
        fontSize=8,
        textColor=GRAY,
        fontName="Helvetica",
        leading=11,
    )

    story = []

    # ─── HEADER BANNER ───────────────────────────────────────────────
    header_data = [
        [Paragraph("Agent Readiness Index", title_style)],
        [Paragraph("AI Readiness Assessment Report", subtitle_style)],
        [Paragraph(f"Session: {session_id[:8].upper()}", subtitle_style)],
    ]
    header_table = Table(header_data, colWidths=[6.5 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
                ("ROUNDEDCORNERS", [8, 8, 8, 8]),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 0.25 * inch))

    # ─── OVERALL SCORE ────────────────────────────────────────────────
    overall_score = score_data.get("overall_score", 0)
    tier = score_data.get("tier", "AI Exploring")
    score_color = get_score_color(overall_score)

    score_label_style = ParagraphStyle(
        "ScoreLabel",
        parent=styles["Normal"],
        fontSize=48,
        textColor=score_color,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    tier_badge_style = ParagraphStyle(
        "TierBadge",
        parent=styles["Normal"],
        fontSize=16,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    tier_sub_style = ParagraphStyle(
        "TierSub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica",
        alignment=TA_CENTER,
    )

    score_data_table = [
        [
            Paragraph(f"{overall_score:.0f}", score_label_style),
            Table(
                [
                    [Paragraph(tier, tier_badge_style)],
                    [Paragraph(get_tier_description(tier)[:200] + "...", tier_sub_style)],
                ],
                colWidths=[3.5 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), score_color),
                        ("BACKGROUND", (0, 1), (-1, 1), NAVY),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ]
                ),
            ),
        ]
    ]
    score_outer = Table(score_data_table, colWidths=[2.5 * inch, 4 * inch])
    score_outer.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (0, 0), LIGHT_GRAY),
                ("TOPPADDING", (0, 0), (0, 0), 20),
                ("BOTTOMPADDING", (0, 0), (0, 0), 20),
            ]
        )
    )
    story.append(score_outer)
    story.append(Spacer(1, 0.2 * inch))

    # ─── PILLAR SCORES ────────────────────────────────────────────────
    story.append(Paragraph("Pillar Breakdown", section_heading))

    pillar_scores = score_data.get("pillar_scores", {})
    pillar_rows = []
    pillar_header = [
        Paragraph("<b>Pillar</b>", body_style),
        Paragraph("<b>Score</b>", body_style),
        Paragraph("<b>Weight</b>", body_style),
        Paragraph("<b>Weighted</b>", body_style),
    ]
    pillar_rows.append(pillar_header)

    for pillar_key, config in PILLAR_CONFIG.items():
        ps = pillar_scores.get(pillar_key, {})
        score = ps.get("score", 0)
        score_col = get_score_color(score)

        pillar_rows.append(
            [
                Paragraph(config["label"], body_style),
                Paragraph(
                    f'<font color="#{score_col.hexval()[2:]}">{score:.0f}/100</font>',
                    body_style,
                ),
                Paragraph(f"{config['weight']*100:.0f}%", body_style),
                Paragraph(f"{ps.get('weighted_score', 0):.1f}", body_style),
            ]
        )

    pillar_table = Table(pillar_rows, colWidths=[2.5 * inch, 1.2 * inch, 1.0 * inch, 1.0 * inch])
    pillar_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(pillar_table)
    story.append(Spacer(1, 0.2 * inch))

    # ─── DETAILED PILLAR ANALYSIS ─────────────────────────────────────
    story.append(Paragraph("Detailed Pillar Analysis", section_heading))

    for pillar_key, config in PILLAR_CONFIG.items():
        ps = pillar_scores.get(pillar_key, {})
        if not ps:
            continue

        score = ps.get("score", 0)
        items = []
        items.append(Paragraph(config["label"], pillar_title_style))
        items.append(
            Paragraph(
                f"Score: {score:.0f}/100 | Weight: {config['weight']*100:.0f}% | Weighted contribution: {ps.get('weighted_score', 0):.1f}",
                small_style,
            )
        )
        items.append(Spacer(1, 4))
        items.append(Paragraph(ps.get("reasoning", ""), body_style))

        if ps.get("evidence"):
            items.append(Paragraph("<b>Evidence:</b>", body_style))
            for ev in ps["evidence"]:
                items.append(Paragraph(f"• {ev}", bullet_style))

        if ps.get("gaps"):
            items.append(Paragraph("<b>Gaps Identified:</b>", body_style))
            for gap in ps["gaps"]:
                items.append(Paragraph(f"• {gap}", bullet_style))

        items.append(Spacer(1, 8))
        items.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
        items.append(Spacer(1, 8))

        story.append(KeepTogether(items))

    # ─── STRENGTHS & GAPS ─────────────────────────────────────────────
    strengths = score_data.get("top_strengths", [])
    gaps = score_data.get("critical_gaps", [])

    sg_data = [
        [
            Paragraph("<b>Top Strengths</b>", ParagraphStyle("SH", parent=styles["Normal"], fontSize=11, textColor=WHITE, fontName="Helvetica-Bold")),
            Paragraph("<b>Critical Gaps</b>", ParagraphStyle("SH", parent=styles["Normal"], fontSize=11, textColor=WHITE, fontName="Helvetica-Bold")),
        ]
    ]
    max_len = max(len(strengths), len(gaps))
    for i in range(max_len):
        s = Paragraph(f"✓ {strengths[i]}", body_style) if i < len(strengths) else Paragraph("", body_style)
        g = Paragraph(f"✗ {gaps[i]}", body_style) if i < len(gaps) else Paragraph("", body_style)
        sg_data.append([s, g])

    sg_table = Table(sg_data, colWidths=[3.25 * inch, 3.25 * inch])
    sg_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), GREEN),
                ("BACKGROUND", (1, 0), (1, 0), RED),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f0fdf4")),
                ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#fef2f2")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(Paragraph("Strengths & Critical Gaps", section_heading))
    story.append(sg_table)
    story.append(Spacer(1, 0.2 * inch))

    # ─── SCORING METHODOLOGY ──────────────────────────────────────────
    story.append(Paragraph("Scoring Methodology", section_heading))
    story.append(
        Paragraph(
            "The Agent Readiness Index is calculated as a weighted sum across 6 pillars. "
            "Each pillar's weight reflects its criticality to successful AI agent deployment.",
            body_style,
        )
    )
    story.append(Spacer(1, 8))

    method_rows = [
        [
            Paragraph("<b>Pillar</b>", body_style),
            Paragraph("<b>Weight</b>", body_style),
            Paragraph("<b>Rationale</b>", body_style),
        ]
    ]
    for pillar_key, config in PILLAR_CONFIG.items():
        method_rows.append(
            [
                Paragraph(config["label"], body_style),
                Paragraph(f"{config['weight']*100:.0f}%", body_style),
                Paragraph(config["weight_reasoning"], small_style),
            ]
        )

    method_table = Table(method_rows, colWidths=[1.5 * inch, 0.6 * inch, 4.4 * inch])
    method_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ]
        )
    )
    story.append(method_table)
    story.append(Spacer(1, 0.2 * inch))

    # ─── TRANSPARENCY ─────────────────────────────────────────────────
    transparency = score_data.get("transparency", {})
    if any(transparency.values()):
        story.append(Paragraph("Data Transparency", section_heading))
        story.append(
            Paragraph(
                "This section documents exactly where each data point came from — ensuring "
                "full transparency in how the score was derived.",
                body_style,
            )
        )
        story.append(Spacer(1, 8))

        for label, key in [
            ("Extracted from URL/Content", "extracted_from_url"),
            ("Extracted from PDF", "extracted_from_pdf"),
            ("Inferred", "inferred"),
            ("From Survey Answers", "from_survey"),
            ("Questions Skipped", "questions_skipped"),
        ]:
            items = transparency.get(key, [])
            if items:
                story.append(Paragraph(f"<b>{label}:</b>", body_style))
                for item in items:
                    story.append(Paragraph(f"• {item}", bullet_style))
                story.append(Spacer(1, 4))

    # ─── FOOTER ───────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * inch))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 8))
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=GRAY,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )
    story.append(
        Paragraph(
            "Agent Readiness Index | Powered by Claude AI | This report is generated based on provided information and AI analysis.",
            footer_style,
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
