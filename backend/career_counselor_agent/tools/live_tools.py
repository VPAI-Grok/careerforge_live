"""
Live-safe tool wrappers for the native audio model.

The native audio model has a known bug (1008 policy violation) with function
calling. These mitigations are applied:

1. Function names have NO underscores (known workaround)
2. ALL parameters are str-only (no list, dict, bool, enum)
3. Tool count is kept minimal to reduce trigger surface
4. Each tool has clear, minimal docstrings
"""
from __future__ import annotations

import json


async def analyzeresume(resume_text: str) -> str:
    """
    Analyzes a resume from plain text and extracts skills, experience,
    education, and career level.

    Args:
        resume_text: The plain text content of the resume.

    Returns:
        A JSON string with structured resume data.
    """
    from .resume import analyze_resume
    result = await analyze_resume(resume_text)
    return json.dumps(result) if isinstance(result, dict) else str(result)


async def searchjobmarket(role: str, location: str = "") -> str:
    """
    Searches the live job market for salary data, demand trends,
    top employers, and hiring insights.

    Args:
        role: The job title to research.
        location: Geographic location for market context.

    Returns:
        A JSON string with salary data, demand trends, top employers.
    """
    from .search_market import search_job_market

    result = await search_job_market(role, location, {})
    return json.dumps(result) if isinstance(result, dict) else str(result)


async def analyzeskillgap(
    currentskills: str,
    targetrole: str,
    location: str = "",
) -> str:
    """
    Compares current skills against target role requirements.

    Args:
        currentskills: Comma-separated list of current skills.
        targetrole: The job title the user is targeting.
        location: Optional geographic location.

    Returns:
        A JSON string with required skills, missing skills, match percentage.
    """
    from .skill_gap import analyze_skill_gap

    skills = [s.strip() for s in currentskills.split(",") if s.strip()]
    result = await analyze_skill_gap(skills, targetrole, location, {})
    return json.dumps(result) if isinstance(result, dict) else str(result)


async def generatecareerroadmap(
    targetrole: str,
    skillgaps: str,
    timelinemonths: str = "12",
) -> str:
    """
    Generates a personalised career roadmap with milestones and action items.

    Args:
        targetrole: The target role for the career transition.
        skillgaps: Comma-separated list of skills to learn.
        timelinemonths: Number of months for the roadmap.

    Returns:
        A JSON string with phased career roadmap.
    """
    from .roadmap import generate_career_roadmap

    gaps = [s.strip() for s in skillgaps.split(",") if s.strip()]

    try:
        months = int(timelinemonths)
    except (ValueError, TypeError):
        months = 12

    result = await generate_career_roadmap({}, targetrole, gaps, months, "", {})
    return json.dumps(result) if isinstance(result, dict) else str(result)


async def findcourses(
    skillgaps: str,
    learningstyle: str = "video",
) -> str:
    """
    Finds the best learning resources for each skill gap.

    Args:
        skillgaps: Comma-separated list of skills to find courses for.
        learningstyle: Preferred format such as video, text, or interactive.

    Returns:
        A JSON string mapping each skill to its curated resource list.
    """
    from .courses import find_courses_for_skills

    gaps = [s.strip() for s in skillgaps.split(",") if s.strip()]
    result = await find_courses_for_skills(gaps, learningstyle, {})
    return json.dumps(result) if isinstance(result, dict) else str(result)


def generatepdfreport(
    careerdatajson: str = "{}",
    username: str = "Career Seeker",
) -> str:
    """
    Generates a professional PDF career roadmap report.

    Args:
        careerdatajson: JSON string containing the career plan data.
        username: The name of the user.

    Returns:
        A base64-encoded PDF string.
    """
    from .pdf_generator import generate_pdf_report

    try:
        career_data = json.loads(careerdatajson) if careerdatajson else {}
    except json.JSONDecodeError:
        career_data = {}

    return generate_pdf_report(career_data, username)
