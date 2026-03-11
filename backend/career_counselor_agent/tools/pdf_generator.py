"""
PDF Report Generator Tool — creates a professional career roadmap PDF.
Uses reportlab for PDF generation.
"""
import io
import json
import os
import base64
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    ListFlowable,
    ListItem,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ── Brand Colors ──────────────────────────────────────────────────────────────
FORGE_BLUE = colors.HexColor("#4F46E5")
FORGE_DARK = colors.HexColor("#1E1B4B")
FORGE_ACCENT = colors.HexColor("#7C3AED")
FORGE_LIGHT_BG = colors.HexColor("#F5F3FF")
FORGE_GREEN = colors.HexColor("#059669")
FORGE_TEXT = colors.HexColor("#1F2937")


def _build_styles():
    """Build custom paragraph styles for the PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "ForgeTitle",
        parent=styles["Title"],
        fontSize=28,
        textColor=FORGE_DARK,
        spaceAfter=6,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "ForgeSubtitle",
        parent=styles["Normal"],
        fontSize=14,
        textColor=FORGE_ACCENT,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        "ForgeSectionHeader",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=FORGE_BLUE,
        spaceBefore=20,
        spaceAfter=10,
        borderWidth=0,
        borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        "ForgeSubHeader",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=FORGE_DARK,
        spaceBefore=12,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "ForgeBody",
        parent=styles["Normal"],
        fontSize=11,
        textColor=FORGE_TEXT,
        leading=16,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "ForgeHighlight",
        parent=styles["Normal"],
        fontSize=11,
        textColor=FORGE_GREEN,
        leading=16,
        spaceAfter=4,
    ))
    return styles


def generate_pdf_report(plan_data: dict, user_name: str = "Career Seeker") -> str:
    """
    Generates a professional CareerForge PDF report from the career plan data.

    Args:
        plan_data: Dict containing the full career plan with short_term and
                   long_term sections (output of generate_career_roadmap).
        user_name: The user's name for personalisation.

    Returns:
        A dict with 'filename' and 'file_base64' keys — the PDF encoded
        as base64 for transmission to the frontend.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = _build_styles()
    story = []

    # ── Title Page ────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("⚡ CareerForge", styles["ForgeTitle"]))
    story.append(Paragraph("Your Personalised Career Roadmap", styles["ForgeSubtitle"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        f"Prepared for <b>{user_name}</b> — {datetime.now().strftime('%B %d, %Y')}",
        styles["ForgeBody"],
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(
        width="80%", thickness=2, color=FORGE_BLUE,
        spaceAfter=20, spaceBefore=10,
    ))

    short_term = plan_data.get("short_term", {})
    long_term = plan_data.get("long_term", {})

    # ── Short-Term Plan ───────────────────────────────────────────────────
    story.append(Paragraph("🎯 Short-Term Action Plan", styles["ForgeSectionHeader"]))
    if short_term.get("summary"):
        story.append(Paragraph(short_term["summary"], styles["ForgeBody"]))

    # Target job titles
    if short_term.get("target_job_titles"):
        story.append(Paragraph("Target Job Titles", styles["ForgeSubHeader"]))
        items = [ListItem(Paragraph(t, styles["ForgeBody"]))
                 for t in short_term["target_job_titles"]]
        story.append(ListFlowable(items, bulletType="bullet"))

    # Monthly plan table
    monthly = short_term.get("monthly_plan", [])
    if monthly:
        story.append(Paragraph("Month-by-Month Roadmap", styles["ForgeSubHeader"]))
        table_data = [["Month", "Focus Area", "Key Action"]]
        for m in monthly:
            table_data.append([
                Paragraph(str(m.get("month", "")), styles["ForgeBody"]),
                Paragraph(str(m.get("focus_area", "")), styles["ForgeBody"]),
                Paragraph(str(m.get("key_action", "")), styles["ForgeBody"]),
            ])
        t = Table(table_data, colWidths=[0.7 * inch, 2.5 * inch, 3.5 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FORGE_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FORGE_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)

    # Quick wins
    if short_term.get("quick_wins"):
        story.append(Paragraph("⚡ Quick Wins — Do This Week", styles["ForgeSubHeader"]))
        items = [ListItem(Paragraph(w, styles["ForgeHighlight"]))
                 for w in short_term["quick_wins"]]
        story.append(ListFlowable(items, bulletType="bullet"))

    # Resume tweaks
    if short_term.get("resume_tweaks"):
        story.append(Paragraph("📝 Resume Tweaks", styles["ForgeSubHeader"]))
        items = [ListItem(Paragraph(tw, styles["ForgeBody"]))
                 for tw in short_term["resume_tweaks"]]
        story.append(ListFlowable(items, bulletType="bullet"))

    # ── Long-Term Vision ──────────────────────────────────────────────────
    story.append(Paragraph("🚀 Long-Term Career Vision", styles["ForgeSectionHeader"]))
    if long_term.get("summary"):
        story.append(Paragraph(long_term["summary"], styles["ForgeBody"]))

    if long_term.get("year_2_goal"):
        story.append(Paragraph(
            f"<b>Year 2 Goal:</b> {long_term['year_2_goal']}", styles["ForgeBody"]
        ))
    if long_term.get("year_5_goal"):
        story.append(Paragraph(
            f"<b>Year 5 Goal:</b> {long_term['year_5_goal']}", styles["ForgeBody"]
        ))

    if long_term.get("promotion_path"):
        story.append(Paragraph("Career Progression", styles["ForgeSubHeader"]))
        path_str = " → ".join(long_term["promotion_path"])
        story.append(Paragraph(f"<b>{path_str}</b>", styles["ForgeBody"]))

    sal = long_term.get("salary_progression", {})
    if sal:
        story.append(Paragraph("💰 Salary Progression", styles["ForgeSubHeader"]))
        sal_data = [
            ["Timeline", "Expected Range"],
            ["Current", Paragraph(str(sal.get("current_estimate", "—")), styles["ForgeBody"])],
            ["Year 2", Paragraph(str(sal.get("year_2", "—")), styles["ForgeBody"])],
            ["Year 5", Paragraph(str(sal.get("year_5", "—")), styles["ForgeBody"])],
        ]
        st = Table(sal_data, colWidths=[1.5 * inch, 4 * inch])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FORGE_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FORGE_LIGHT_BG]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(st)

    if long_term.get("side_hustle_ideas"):
        story.append(Paragraph("💡 Side Hustle Ideas", styles["ForgeSubHeader"]))
        items = [ListItem(Paragraph(s, styles["ForgeBody"]))
                 for s in long_term["side_hustle_ideas"]]
        story.append(ListFlowable(items, bulletType="bullet"))

    # ── Potential Blockers ────────────────────────────────────────────────
    blockers = plan_data.get("potential_blockers", [])
    if blockers:
        story.append(Paragraph("⚠️ Watch Out For", styles["ForgeSectionHeader"]))
        items = [ListItem(Paragraph(b, styles["ForgeBody"])) for b in blockers]
        story.append(ListFlowable(items, bulletType="bullet"))

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * inch))
    story.append(HRFlowable(
        width="100%", thickness=1, color=FORGE_BLUE,
        spaceAfter=10, spaceBefore=10,
    ))
    story.append(Paragraph(
        "Generated by CareerForge — Powered by Gemini AI",
        ParagraphStyle("Footer", fontSize=9, textColor=colors.gray, alignment=TA_CENTER),
    ))

    # ── Build & encode ────────────────────────────────────────────────────
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"CareerForge_Plan_{user_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return {
        "filename": filename,
        "file_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
        "size_kb": round(len(pdf_bytes) / 1024, 1),
    }
