"""
Skill Gap Analyzer Tool — compares user skills vs. target role requirements.
Enhanced with user profile context and Google Search grounding.
"""
import asyncio
import json

from google import genai
from google.genai import types


def _get_client() -> genai.Client:
    from career_counselor_agent.api.server import api_key_ctx
    key = api_key_ctx.get()
    return genai.Client(api_key=key) if key else genai.Client()


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
            "error": "Failed to parse skill gap data",
            "raw_snippet": raw[:500],
        }


async def analyze_skill_gap(
    current_skills: list[str],
    target_role: str,
    location: str = "",
    user_profile: dict = {},
) -> dict:
    """
    Compares the user's current skills against the requirements for a target
    role. Uses the full user profile for personalised, context-aware analysis.

    Uses Google Search grounding for current market data.

    Args:
        current_skills: A list of skill strings the user currently possesses.
        target_role: The job title or role the user is targeting.
        location: Optional geographic location for salary/market context.
        user_profile: Optional dict with user profile data for personalised analysis.

    Returns:
        A dict with keys: required_skills, missing_skills, priority_skills,
        existing_strengths, match_percentage, estimated_months_to_ready,
        salary_range, market_demand, personalised_notes.
    """
    client = _get_client()
    location_ctx = f" in {location}" if location else ""

    # Build profile context for the prompt
    profile_ctx = ""
    if user_profile:
        profile_lines = []
        if user_profile.get("years_experience"):
            profile_lines.append(f"Years of experience: {user_profile['years_experience']}")
        if user_profile.get("education_level"):
            profile_lines.append(f"Education: {user_profile['education_level']}")
        if user_profile.get("learning_hours_per_week"):
            profile_lines.append(f"Available learning time: {user_profile['learning_hours_per_week']} hours/week")
        if user_profile.get("leadership_vs_ic"):
            profile_lines.append(f"Career track: {user_profile['leadership_vs_ic']}")
        if user_profile.get("soft_skills"):
            profile_lines.append(f"Soft skills: {', '.join(user_profile['soft_skills'])}")
        if user_profile.get("has_portfolio") is not None:
            profile_lines.append(f"Has portfolio/side projects: {'Yes' if user_profile['has_portfolio'] else 'No'}")
        if user_profile.get("risk_tolerance"):
            profile_lines.append(f"Risk tolerance: {user_profile['risk_tolerance']}/10")
        if user_profile.get("burnout_level"):
            profile_lines.append(f"Burnout level: {user_profile['burnout_level']}/10")
        if user_profile.get("timeline"):
            profile_lines.append(f"Target timeline: {user_profile['timeline']}")
        if profile_lines:
            profile_ctx = "\n\nUser Profile Context:\n" + "\n".join(f"- {l}" for l in profile_lines)

    prompt = f"""\
You are a senior technical hiring expert and career coach with access to
current job market data.

User's current skills: {current_skills}
Target role: {target_role}{location_ctx}{profile_ctx}

Search for the LATEST job postings and market data for "{target_role}"{location_ctx}
to inform your analysis.

IMPORTANT PERSONALISATION RULES:
- If the user has limited learning time, prioritise skills that give the HIGHEST ROI
- If burnout level is high (>7), recommend a manageable learning pace
- Consider their education level when assessing credential gaps
- Factor in their career track preference (leadership vs IC) when ranking skills
- If they have a portfolio, deprioritise "build portfolio" as a recommendation
- Adjust estimated_months_to_ready based on their available learning hours/week

Return a JSON object with the following fields:
- required_skills: complete list of skills needed to be competitive for "{target_role}" RIGHT NOW (2025-2026)
- missing_skills: skills the user currently lacks
- priority_skills: top 5 missing skills to learn FIRST for the highest ROI (considering their available time and situation)
- existing_strengths: skills the user already has that are highly relevant
- match_percentage: integer 0-100, how qualified the user is right now
- estimated_months_to_ready: realistic integer estimate based on their available learning hours/week
- salary_range: object with "min", "max", "median" integers (annual, USD){location_ctx}
- market_demand: one of "very_high" | "high" | "moderate" | "low" — current demand
- personalised_notes: 2-3 sentences of coaching advice specific to THIS person's situation

Return ONLY valid JSON — no markdown, no explanation, no code fences.
"""
    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            ),
            timeout=30.0,
        )
        return _parse_json(response.text)
    except asyncio.TimeoutError:
        return {"error": "Skill gap analysis timed out", "target_role": target_role}
    except Exception as e:
        return {"error": str(e)[:200], "target_role": target_role}
