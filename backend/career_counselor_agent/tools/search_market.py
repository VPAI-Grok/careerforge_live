"""
Job Market Research Tool — uses Google Search grounding for live market data.
Enhanced with user profile context for personalised filtering.
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
            "error": "Failed to parse market data",
            "raw_snippet": raw[:500],
        }


async def search_job_market(role: str, location: str = "", user_profile: dict = {}) -> dict:
    """
    Searches the live job market for current salary data, demand trends,
    top employers, and hiring insights for a given role and location.
    Filters and personalises results based on user profile.

    Uses Google Search grounding for up-to-date, real-world results.

    Args:
        role: The job title to research (e.g. "Product Marketing Manager").
        location: Geographic location for market context.
        user_profile: Optional dict with user profile for personalised results.

    Returns:
        A dict with salary data, demand trends, top employers, requirements,
        and personalised recommendations.
    """
    client = _get_client()
    location_ctx = f" in {location}" if location else ""

    # Build profile-aware search context
    filter_ctx = ""
    if user_profile:
        filters = []
        if user_profile.get("work_style") and user_profile["work_style"] != "No preference":
            filters.append(f"Focus on {user_profile['work_style']} positions")
        if user_profile.get("company_size_preference") and user_profile["company_size_preference"] != "No preference":
            filters.append(f"Prefer {user_profile['company_size_preference']} companies")
        if user_profile.get("target_salary"):
            filters.append(f"Target salary range: ${user_profile['target_salary']:,}+")
        if user_profile.get("current_salary"):
            filters.append(f"Current salary: ${user_profile['current_salary']:,} (looking for upward move)")
        if user_profile.get("years_experience"):
            filters.append(f"Years of experience: {user_profile['years_experience']}")
        if user_profile.get("deal_breakers"):
            filters.append(f"Must AVOID: {', '.join(user_profile['deal_breakers'])}")
        if user_profile.get("leadership_vs_ic"):
            filters.append(f"Track preference: {user_profile['leadership_vs_ic']}")
        if user_profile.get("motivation"):
            filters.append(f"Career priorities: {', '.join(user_profile['motivation'])}")
        if filters:
            filter_ctx = "\n\nUSER PREFERENCES (filter results accordingly):\n" + "\n".join(f"- {f}" for f in filters)

    prompt = f"""\
You are a career market research analyst. Search for the LATEST job market
data for "{role}"{location_ctx}.

Use current job postings, salary surveys, and market reports to build
an accurate picture of the job market RIGHT NOW (2025-2026).{filter_ctx}

PERSONALISATION RULES:
- Filter top_employers based on company size preference (if specified)
- Only include remote/hybrid opportunities if that's their work style preference
- Flag roles that match their deal breakers as warnings
- Highlight roles that align with their career priorities/motivation
- Adjust salary ranges for their experience level

Return a JSON object with exactly these fields:
{{
  "role": "{role}",
  "location": "{location or 'Global'}",
  "salary": {{
    "currency": "USD",
    "entry_level": {{ "min": <int>, "max": <int> }},
    "mid_level": {{ "min": <int>, "max": <int> }},
    "senior_level": {{ "min": <int>, "max": <int> }},
    "median": <int>,
    "salary_trend": "one of: rising | stable | declining",
    "trend_note": "1 sentence about recent salary movement",
    "negotiation_leverage": "1 sentence on how strong the candidate's negotiating position is"
  }},
  "demand": {{
    "level": "one of: very_high | high | moderate | low",
    "open_positions_estimate": "<string like '15,000+ openings'>",
    "yoy_growth": "string like '+12% year over year'",
    "remote_availability": "one of: very_common | common | limited | rare",
    "best_time_to_apply": "1 sentence about hiring seasonality"
  }},
  "top_employers": ["5-8 top companies FILTERED by user preferences"],
  "must_have_skills": ["5-7 most commonly required skills"],
  "nice_to_have_skills": ["3-5 skills that give candidates an edge"],
  "certifications_that_help": ["relevant certifications"],
  "interview_insights": "1-2 sentences about what interviewers focus on",
  "market_summary": "2-3 sentence summary personalised to user's situation",
  "personalised_tip": "1 specific tip for THIS user based on their profile and the market data"
}}

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
        return {"error": "Job market search timed out", "role": role}
    except Exception as e:
        return {"error": str(e)[:200], "role": role}
