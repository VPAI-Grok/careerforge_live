"""
Course Finder Tool — finds learning resources for priority skill gaps.
Enhanced with user profile context for personalised recommendations.

IMPORTANT: All skill lookups run in PARALLEL to avoid blocking the Live API
WebSocket connection (sequential calls caused 15-25s blocking → timeout).
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
            "resources": [],
            "error": "JSON parsing failed",
            "raw": raw[:300],
        }


async def _fetch_one_skill(
    client: genai.Client,
    skill: str,
    learning_style: str,
    budget_ctx: str,
) -> tuple[str, dict]:
    """Fetch courses for a single skill with a timeout."""
    prompt = f"""\
You are a learning resource curator. Find the top 3 {learning_style} learning
resources for "{skill}" from YouTube, Coursera, freeCodeCamp, edX, Udemy, or
official docs.{budget_ctx}

Return a JSON object:
{{
  "skill": "{skill}",
  "resources": [
    {{
      "title": "<course title>",
      "platform": "<platform>",
      "url": "<URL>",
      "is_free": <true|false>,
      "estimated_hours": <int>,
      "why_recommended": "<1 sentence>"
    }}
  ]
}}

Return ONLY valid JSON.
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
        return skill, _parse_json(response.text)
    except asyncio.TimeoutError:
        return skill, {"skill": skill, "resources": [], "error": "Timed out"}
    except Exception as e:
        return skill, {"skill": skill, "resources": [], "error": str(e)[:200]}


async def find_courses_for_skills(
    skill_gaps: list[str],
    learning_style: str = "video",
    user_profile: dict = {},
) -> dict:
    """
    Finds the best learning resources for each priority skill gap.
    Personalises recommendations based on user's available time, budget, and style.

    Uses Gemini with Google Search grounding for up-to-date results.
    All skill lookups run in PARALLEL to avoid blocking the Live API connection.

    Args:
        skill_gaps: List of skill names to find courses for (top 3 used).
        learning_style: Preferred format — "video", "text", or "interactive".
        user_profile: Optional dict with user profile for personalised filtering.

    Returns:
        A dict mapping each skill name to its curated resource list.
    """
    client = _get_client()

    # Build budget & time context from profile
    budget_ctx = ""
    if user_profile:
        budget_parts = []
        if user_profile.get("learning_hours_per_week"):
            hrs = user_profile["learning_hours_per_week"]
            budget_parts.append(f"Available time: {hrs} hours/week")
        if user_profile.get("burnout_level") and user_profile["burnout_level"] >= 7:
            budget_parts.append("High burnout — prefer engaging/interactive resources")
        if user_profile.get("has_portfolio") is False:
            budget_parts.append("Needs portfolio — prefer project-based courses")
        if budget_parts:
            budget_ctx = "\n\nUser Context:\n" + "\n".join(f"- {b}" for b in budget_parts)

    # Run ALL skill lookups in PARALLEL (not sequentially!)
    tasks = [
        _fetch_one_skill(client, skill, learning_style, budget_ctx)
        for skill in skill_gaps[:3]  # Limit to 3 to keep it fast
    ]
    pairs = await asyncio.gather(*tasks, return_exceptions=True)

    results = {}
    for item in pairs:
        if isinstance(item, Exception):
            continue
        skill_name, data = item
        results[skill_name] = data

    return results
