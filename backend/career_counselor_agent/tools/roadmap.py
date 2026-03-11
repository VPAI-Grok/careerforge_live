"""
Career Roadmap Generator Tool — produces short-term + long-term career plans.
Deeply personalised with user profile context (risk, burnout, finances, motivation).
"""
import asyncio
import json

from google import genai


def _get_client() -> genai.Client:
    return genai.Client()


def _parse_json(raw: str) -> dict:
    """Best-effort JSON extraction from Gemini output."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse roadmap data",
            "raw_snippet": raw[:500],
        }


async def generate_career_roadmap(
    profile: dict,
    target_role: str,
    skill_gaps: list[str],
    timeline_months: int = 12,
    preferences: str = "",
    user_profile: dict = {},
) -> dict:
    """
    Generates a deeply personalised career roadmap with both short-term
    tactics and long-term strategic vision. Adapts aggressiveness, pacing,
    and focus areas based on the user's risk tolerance, burnout level,
    financial runway, motivation, and life obligations.

    Args:
        profile: Dict containing the user's resume analysis (from analyze_resume).
        target_role: The job title the user is working towards.
        skill_gaps: List of priority skill gaps to fill.
        timeline_months: Short-term plan length in months (default 12).
        preferences: Optional user preferences like "remote only", "aggressive".
        user_profile: Optional dict with full user profile for deep personalisation.

    Returns:
        A dict with both short-term and long-term roadmap components,
        personalised to the user's complete situation.
    """
    client = _get_client()
    pref_ctx = f"\nUser preferences: {preferences}" if preferences else ""

    # Build rich profile context
    profile_ctx = ""
    if user_profile:
        ctx_parts = []
        if user_profile.get("risk_tolerance"):
            ctx_parts.append(f"Risk tolerance: {user_profile['risk_tolerance']}/10")
        if user_profile.get("burnout_level"):
            ctx_parts.append(f"Burnout level: {user_profile['burnout_level']}/10")
        if user_profile.get("satisfaction_level"):
            ctx_parts.append(f"Job satisfaction: {user_profile['satisfaction_level']}/10")
        if user_profile.get("confidence_level"):
            ctx_parts.append(f"Interview/networking confidence: {user_profile['confidence_level']}/10")
        if user_profile.get("savings_months") is not None:
            ctx_parts.append(f"Financial runway: {user_profile['savings_months']} months of savings")
        if user_profile.get("obligations"):
            ctx_parts.append(f"Financial obligations: {', '.join(user_profile['obligations'])}")
        if user_profile.get("current_salary") is not None:
            ctx_parts.append(f"Current salary: ${user_profile['current_salary']:,}")
        if user_profile.get("target_salary") is not None:
            ctx_parts.append(f"Target salary: ${user_profile['target_salary']:,}")
        if user_profile.get("motivation"):
            ctx_parts.append(f"Primary motivations: {', '.join(user_profile['motivation'])}")
        if user_profile.get("leadership_vs_ic"):
            ctx_parts.append(f"Career track: {user_profile['leadership_vs_ic']}")
        if user_profile.get("work_style"):
            ctx_parts.append(f"Work style: {user_profile['work_style']}")
        if user_profile.get("company_size_preference"):
            ctx_parts.append(f"Company size preference: {user_profile['company_size_preference']}")
        if user_profile.get("deal_breakers"):
            ctx_parts.append(f"Deal breakers: {', '.join(user_profile['deal_breakers'])}")
        if user_profile.get("pain_points"):
            ctx_parts.append(f"Career pain points: {', '.join(user_profile['pain_points'])}")
        if user_profile.get("learning_hours_per_week"):
            ctx_parts.append(f"Available learning time: {user_profile['learning_hours_per_week']} hrs/week")
        if user_profile.get("location"):
            ctx_parts.append(f"Location: {user_profile['location']}")
            if user_profile.get("willing_to_relocate"):
                ctx_parts.append("Open to relocation")
        if user_profile.get("has_portfolio") is not None:
            ctx_parts.append(f"Has portfolio: {'Yes' if user_profile['has_portfolio'] else 'No'}")
        if user_profile.get("timeline"):
            ctx_parts.append(f"Target timeline: {user_profile['timeline']}")
        if ctx_parts:
            profile_ctx = "\n\nDETAILED USER PROFILE:\n" + "\n".join(f"- {p}" for p in ctx_parts)

    prompt = f"""\
Create a comprehensive, deeply personalised career roadmap for someone
transitioning to the role of {target_role}.

User Resume Profile: {json.dumps(profile)}
Priority Skill Gaps to Fill: {skill_gaps}
Short-Term Timeline: {timeline_months} months{pref_ctx}{profile_ctx}

CRITICAL PERSONALISATION RULES — read these carefully:

1. RISK & FINANCES: If risk_tolerance is low (≤3) OR savings is < 3 months OR
   they have heavy obligations → recommend CONSERVATIVE path: keep current job,
   learn on the side, transition gradually. If risk is high (≥8) AND savings ≥ 6
   months → can recommend bolder moves (career break, bootcamp, freelancing).

2. BURNOUT: If burnout_level ≥ 7 → Month 1 should be "Recovery & Reset" — lighter
   activities, self-care, NOT intense study. Build up gradually. Acknowledge
   burnout in the summary.

3. MOTIVATION-DRIVEN FOCUS:
   - If "Money" is primary → emphasise salary negotiation, high-paying specialties
   - If "Impact" → emphasise mission-driven companies, social impact roles
   - If "Work-Life Balance" → emphasise remote roles, flexible companies, boundaries
   - If "Growth" → emphasise skill-building, mentorship, challenging roles
   - If "Passion" → emphasise alignment with interests, creative roles

4. CONFIDENCE: If confidence_level ≤ 3 → include confidence-building milestones
   (informational interviews before real ones, mock interviews, small networking wins).

5. LEARNING PACE: Scale monthly goals to their available learning_hours_per_week.
   5 hrs/week = manageable pace. 15+ hrs/week = accelerated track.

6. WORK PREFERENCES: Only recommend roles matching their work_style. Respect
   deal_breakers absolutely. Factor in company_size_preference.

7. SALARY: If current_salary and target_salary are provided, include specific
   salary negotiation tactics and realistic progression.

Return a JSON object with the following structure:

{{
  "short_term": {{
    "summary": "2-3 sentence overview personalised to their situation (reference their specific pain points, burnout level, motivation)",
    "target_job_titles": ["3-5 specific job titles filtered by their work style and preferences"],
    "monthly_plan": [
      {{
        "month": 1,
        "focus_area": "string",
        "goals": ["goal1", "goal2"],
        "milestones": ["milestone1"],
        "key_action": "the single most important thing to do this month",
        "hours_needed": <int based on their learning capacity>
      }}
    ],
    "resume_tweaks": ["specific changes to make to the resume"],
    "application_strategy": "personalised paragraph — conservative or aggressive based on their risk profile",
    "quick_wins": ["3 things they can do THIS WEEK to start momentum"],
    "success_metrics": ["measurable indicators to track progress"],
    "salary_negotiation": "specific tactics for getting from current to target salary (if salary data provided)"
  }},
  "long_term": {{
    "summary": "2-3 sentence vision for 2-5 year career trajectory aligned with their motivation",
    "year_2_goal": "where they should be in 2 years",
    "year_5_goal": "where they should be in 5 years",
    "promotion_path": ["sequential role progression aligned with leadership_vs_ic preference"],
    "pivot_options": ["2-3 alternative career directions if they want to pivot later"],
    "leadership_milestones": ["key achievements to target (adjusted for IC vs leadership track)"],
    "salary_progression": {{
      "current_estimate": "string with dollar range",
      "year_2": "string with dollar range",
      "year_5": "string with dollar range"
    }},
    "side_hustle_ideas": ["1-2 realistic side income ideas aligned with their motivation"],
    "industry_trends": "paragraph about where this field is heading in 5 years"
  }},
  "wellbeing_plan": {{
    "burnout_recovery": "specific recommendations if burnout is high, or null",
    "work_life_boundaries": "advice for maintaining balance during transition",
    "confidence_building": "specific steps if confidence is low, or null"
  }},
  "financial_plan": {{
    "risk_assessment": "safe to quit / transition while employed / need more runway",
    "savings_recommendation": "specific advice based on their financial situation",
    "investment_in_learning": "recommended budget/free resources based on their constraints"
  }},
  "potential_blockers": ["common pitfalls personalised to their situation and how to avoid them"]
}}

Return ONLY valid JSON — no markdown, no explanation, no code fences.
"""
    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            ),
            timeout=45.0,  # Roadmap generation is complex, allow 45s
        )
        return _parse_json(response.text)
    except asyncio.TimeoutError:
        return {"error": "Roadmap generation timed out", "target_role": target_role}
    except Exception as e:
        return {"error": str(e)[:200], "target_role": target_role}
