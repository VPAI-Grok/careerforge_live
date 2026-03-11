"""
Resume Analyzer Tool — supports both text and vision (PDF / image) input.
"""
import base64
import json
import mimetypes

from google import genai
from google.genai import types


def _get_client() -> genai.Client:
    """Return a Gemini client using the configured credentials."""
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
            "error": "Failed to parse structured resume data",
            "raw_snippet": raw[:500],
        }


_EXTRACT_PROMPT = """\
You are an expert resume analyst. Analyze the resume provided and return a JSON
object with EXACTLY these fields:

- name: the candidate's full name
- email: contact email (or null)
- phone: contact phone (or null)
- skills: list of technical and soft skills
- experience_years: total years of professional experience (integer)
- current_role: most recent job title
- education: highest degree + field of study
- career_level: one of "entry" | "mid" | "senior" | "lead" | "executive"
- industries: list of industries the person has worked in
- achievements: top 3 quantified achievements (strings)
- work_history: list of objects with keys: company, role, start_year, end_year, highlights

Return ONLY valid JSON — no markdown, no explanation, no code fences.
"""


async def analyze_resume(resume_text: str) -> dict:
    """
    Extracts and structures key information from a resume.
    Returns skills, experience, education, career level, and more.

    Args:
        resume_text: The plain text content of the user's resume.

    Returns:
        A dict with keys: name, skills, experience_years, current_role,
        education, career_level, industries, achievements, work_history.
    """
    client = _get_client()

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{_EXTRACT_PROMPT}\n\nResume:\n{resume_text}",
    )
    return _parse_json(response.text)


async def analyze_resume_vision(file_base64: str, mime_type: str = "application/pdf") -> dict:
    """
    Extracts and structures key information from a resume image or PDF
    using Gemini Vision. Supports scanned photos, screenshots, and PDFs.

    Args:
        file_base64: Base64-encoded string of the resume file (PDF or image).
        mime_type: MIME type of the file, e.g. "application/pdf" or "image/png".

    Returns:
        A dict with keys: name, skills, experience_years, current_role,
        education, career_level, industries, achievements, work_history.
    """
    client = _get_client()

    file_bytes = base64.b64decode(file_base64)
    file_part = types.Part(
        inline_data=types.Blob(mime_type=mime_type, data=file_bytes)
    )

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text=_EXTRACT_PROMPT),
                    file_part,
                ],
            )
        ],
    )
    return _parse_json(response.text)
