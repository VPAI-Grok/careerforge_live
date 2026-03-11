"""
User Profile Model — comprehensive profiling for personalised career coaching.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Complete user profile for personalised career coaching."""

    # ── Career Context ────────────────────────────────────────────────────
    current_role: str = ""
    industry: str = ""
    years_experience: int = 0
    education_level: str = ""        # "High School", "Bachelor's", "Master's", "PhD"

    # ── Emotional & Satisfaction ──────────────────────────────────────────
    satisfaction_level: int = Field(default=5, ge=1, le=10)
    burnout_level: int = Field(default=3, ge=1, le=10)
    confidence_level: int = Field(default=5, ge=1, le=10)
    pain_points: list[str] = Field(default_factory=list)
    # e.g. ["Bad manager", "No growth", "Underpaid", "Burnout", "Bored",
    #        "Toxic culture", "Job insecurity", "No work-life balance"]

    # ── Goals & Aspirations ───────────────────────────────────────────────
    dream_roles: list[str] = Field(default_factory=list)
    motivation: list[str] = Field(default_factory=list)
    # e.g. ["Money", "Impact", "Work-Life Balance", "Growth", "Passion", "Status"]
    leadership_vs_ic: str = "Both"   # "Lead people" | "Go deep technically" | "Both"
    timeline: str = "1 year"         # "3 months" | "6 months" | "1 year" | "2+ years"

    # ── Skills ────────────────────────────────────────────────────────────
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    has_portfolio: bool = False

    # ── Work Preferences ──────────────────────────────────────────────────
    work_style: str = "Hybrid"       # "Remote" | "Hybrid" | "On-site"
    company_size_preference: str = "No preference"
    # "Startup" | "SMB" | "Enterprise" | "No preference"
    deal_breakers: list[str] = Field(default_factory=list)
    # e.g. ["Travel >25%", "On-call", "Relocation required", "No remote"]

    # ── Location ──────────────────────────────────────────────────────────
    location: str = ""
    willing_to_relocate: bool = False

    # ── Financial Context ─────────────────────────────────────────────────
    current_salary: int | None = None
    target_salary: int | None = None
    savings_months: int | None = None       # months of runway
    obligations: list[str] = Field(default_factory=list)
    # e.g. ["Mortgage", "Kids", "Student loans", "Car payment", "Caregiving"]

    # ── Risk & Learning ───────────────────────────────────────────────────
    risk_tolerance: int = Field(default=5, ge=1, le=10)
    learning_hours_per_week: int = 5


def build_profile_context(profile: UserProfile) -> str:
    """
    Converts a UserProfile into a concise text block that can be injected
    into any LLM prompt for context-aware responses.
    """
    lines: list[str] = ["USER PROFILE CONTEXT:"]

    if profile.current_role:
        lines.append(f"- Current role: {profile.current_role} ({profile.years_experience} years experience)")
    if profile.industry:
        lines.append(f"- Industry: {profile.industry}")
    if profile.education_level:
        lines.append(f"- Education: {profile.education_level}")
    if profile.location:
        reloc = " (open to relocation)" if profile.willing_to_relocate else " (not open to relocation)"
        lines.append(f"- Location: {profile.location}{reloc}")

    lines.append(f"- Job satisfaction: {profile.satisfaction_level}/10")
    lines.append(f"- Burnout level: {profile.burnout_level}/10")
    lines.append(f"- Confidence level: {profile.confidence_level}/10")
    lines.append(f"- Risk tolerance: {profile.risk_tolerance}/10")

    if profile.pain_points:
        lines.append(f"- Pain points: {', '.join(profile.pain_points)}")

    if profile.dream_roles:
        lines.append(f"- Dream roles: {', '.join(profile.dream_roles)}")
    if profile.motivation:
        lines.append(f"- Primary motivations: {', '.join(profile.motivation)}")
    lines.append(f"- Career track preference: {profile.leadership_vs_ic}")
    lines.append(f"- Target timeline: {profile.timeline}")

    if profile.technical_skills:
        lines.append(f"- Technical skills: {', '.join(profile.technical_skills)}")
    if profile.soft_skills:
        lines.append(f"- Soft skills: {', '.join(profile.soft_skills)}")
    lines.append(f"- Has portfolio/side projects: {'Yes' if profile.has_portfolio else 'No'}")

    lines.append(f"- Work style preference: {profile.work_style}")
    lines.append(f"- Company size preference: {profile.company_size_preference}")
    if profile.deal_breakers:
        lines.append(f"- Deal breakers: {', '.join(profile.deal_breakers)}")

    if profile.current_salary is not None:
        lines.append(f"- Current salary: ${profile.current_salary:,}")
    if profile.target_salary is not None:
        lines.append(f"- Target salary: ${profile.target_salary:,}")
    if profile.savings_months is not None:
        lines.append(f"- Financial runway: {profile.savings_months} months of savings")
    if profile.obligations:
        lines.append(f"- Financial obligations: {', '.join(profile.obligations)}")

    lines.append(f"- Learning capacity: {profile.learning_hours_per_week} hours/week")

    # ── Coaching style hints ──────────────────────────────────────────────
    lines.append("")
    lines.append("COACHING STYLE ADJUSTMENTS:")

    if profile.burnout_level >= 7:
        lines.append("⚠️ HIGH BURNOUT — be extra gentle, recommend recovery before intense pivots.")
    if profile.confidence_level <= 3:
        lines.append("⚠️ LOW CONFIDENCE — be extra encouraging, frame everything as achievable.")
    if profile.risk_tolerance <= 3 or (profile.savings_months and profile.savings_months < 3):
        lines.append("⚠️ LOW RISK TOLERANCE/TIGHT FINANCES — recommend conservative, keep-job-while-learning approach.")
    if profile.risk_tolerance >= 8 and (profile.savings_months and profile.savings_months >= 6):
        lines.append("🚀 HIGH RISK TOLERANCE + RUNWAY — can recommend bold moves like career breaks for learning.")
    if profile.satisfaction_level <= 3:
        lines.append("🔴 VERY UNSATISFIED — acknowledge frustration, prioritize quick-win strategies.")

    return "\n".join(lines)
