"""
CareerForge Live — ADK Root Agent (Forge)

Multi-agent architecture:
  • root_agent  (text) — orchestrator using gemini-2.5-flash
  • live_agent  (audio) — orchestrator using native-audio model
  Each parent delegates to specialized sub-agents:
    → resume_analyst       — resume analysis (text & vision)
    → market_researcher    — job market search with Google Search grounding
    → career_planner       — skill gaps, roadmaps, courses & PDF reports
"""
from __future__ import annotations

import pathlib
import career_counselor_agent.config  # MUST BE FIRST to setup env/API keys

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from .tools.resume import analyze_resume, analyze_resume_vision
from .tools.skill_gap import analyze_skill_gap
from .tools.roadmap import generate_career_roadmap
from .tools.courses import find_courses_for_skills
from .tools.search_market import search_job_market
from .tools.pdf_generator import generate_pdf_report

# ── Constants ─────────────────────────────────────────────────────────────────
APP_NAME = "careerforge"
_PROMPT_PATH = pathlib.Path(__file__).parent / "prompts" / "system_prompt.txt"
_SYSTEM_INSTRUCTION = _PROMPT_PATH.read_text(encoding="utf-8")

# Model names
_TEXT_MODEL = "gemini-2.5-flash"
_AUDIO_MODEL = "gemini-2.5-flash-native-audio-latest"

# ── Sub-Agent Definitions ─────────────────────────────────────────────────────

# 1) Resume Analyst — handles all resume-related analysis
_RESUME_INSTRUCTION = """You are the Resume Analyst sub-agent of Forge, the CareerForge AI career counselor.
Your specialty is analysing resumes — both text-based and vision-based (PDF/image).

When you receive a resume:
1. Thoroughly extract all skills, experience, education, certifications, and achievements.
2. Identify strengths and areas for improvement.
3. Present a structured summary naturally in conversation.

Be warm and encouraging. Highlight the candidate's strongest points first,
then gently note gaps as "growth opportunities." Keep responses concise for voice mode.

After you finish the analysis, transfer back to the main agent (forge / forge_live)
so they can continue the coaching session."""

_RESUME_DESCRIPTION = (
    "Resume Analyst — call this agent when the user needs resume analysis, "
    "either from pasted text or an uploaded PDF/image file."
)

# 2) Market Researcher — handles job market searches
_MARKET_INSTRUCTION = """You are the Market Researcher sub-agent of Forge, the CareerForge AI career counselor.
Your specialty is live job market intelligence using Google Search grounding.

When asked to research a role or market:
1. Call search_job_market with the role, location, and user profile.
2. Present salary ranges, demand levels, top employers, and required skills.
3. Personalise insights to the user's specific situation and preferences.

Use data-driven language: "According to current postings..." and "The market shows..."
Keep responses concise for voice mode — 2-3 key insights, then ask if they want more detail.

After delivering the market insights, transfer back to the main agent (forge / forge_live)."""

_MARKET_DESCRIPTION = (
    "Market Researcher — call this agent when the user needs job market data, "
    "salary info, demand trends, or employer insights for a specific role or location."
)

# 3) Career Planner — handles skill gaps, roadmaps, courses, and reports
_PLANNER_INSTRUCTION = """You are the Career Planner sub-agent of Forge, the CareerForge AI career counselor.
Your specialty is building actionable career plans tailored to each user's unique situation.

Your capabilities:
- analyze_skill_gap: Compare current skills against target role requirements
- generate_career_roadmap: Build a time-phased career transition plan
- find_courses_for_skills: Recommend specific courses within budget/time constraints
- generate_pdf_report: Create a professional PDF deliverable with the full plan

Workflow:
1. First, analyze skill gaps with the user's profile context.
2. Use gap data to generate a personalised career roadmap.
3. Recommend courses that fit their learning style, budget, and time.
4. If the user wants a takeaway, generate a PDF report.

Adapt your plans based on:
- Burnout level (≥7: lighter first month, focus on recovery)
- Risk tolerance + savings (low: keep-your-job strategies)
- Learning hours/week (realistic timeline)

Keep responses concise for voice mode. Walk through the plan step-by-step.

After delivering the plan, transfer back to the main agent (forge / forge_live)."""

_PLANNER_DESCRIPTION = (
    "Career Planner — call this agent when the user needs skill gap analysis, "
    "a career roadmap, course recommendations, or a PDF career report."
)

# ── Session memory (shared across all agents) ─────────────────────────────────
session_service = InMemorySessionService()


# ── Helper: create a set of sub-agents for a given model ──────────────────────
def _make_sub_agents(model: str) -> list[Agent]:
    """Creates the three specialized sub-agents for the given model."""
    prefix = "live_" if "native-audio" in model else ""

    resume_analyst = Agent(
        name=f"{prefix}resume_analyst",
        model=model,
        description=_RESUME_DESCRIPTION,
        instruction=_RESUME_INSTRUCTION,
        tools=[analyze_resume, analyze_resume_vision],
    )

    market_researcher = Agent(
        name=f"{prefix}market_researcher",
        model=model,
        description=_MARKET_DESCRIPTION,
        instruction=_MARKET_INSTRUCTION,
        tools=[search_job_market],
    )

    career_planner = Agent(
        name=f"{prefix}career_planner",
        model=model,
        description=_PLANNER_DESCRIPTION,
        instruction=_PLANNER_INSTRUCTION,
        tools=[
            analyze_skill_gap,
            generate_career_roadmap,
            find_courses_for_skills,
            generate_pdf_report,
        ],
    )

    return [resume_analyst, market_researcher, career_planner]


# ── Parent Agent Descriptions ─────────────────────────────────────────────────
_PARENT_DESCRIPTION = (
    "Forge — an empathetic, world-class AI career counselor who reads "
    "your resume (text or vision), interviews you naturally, researches "
    "the live job market, and builds a personalised career roadmap with "
    "both short-term tactics and long-term vision. Delegates specialised "
    "tasks to expert sub-agents."
)

# ── Text Chat Agent (standard generateContent) ───────────────────────────────
root_agent = Agent(
    name="forge",
    model=_TEXT_MODEL,
    description=_PARENT_DESCRIPTION,
    instruction=_SYSTEM_INSTRUCTION,
    sub_agents=_make_sub_agents(_TEXT_MODEL),
)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# ── Dedicated Report Agent (standard generateContent) ────────────────────────
# This agent has ALL tools directly attached (no sub-agents) to reliably
# execute the multi-step post-session report generation workflow without
# getting stuck in handoff loops or hallucinating tools.
report_agent = Agent(
    name="report_generator",
    model=_TEXT_MODEL,
    description="Dedicated agent for generating end-of-session career reports.",
    instruction=(
        "You are Forge's background report generation engine.\n"
        "Your only job is to follow the user's multi-step workflow request to build a full career plan.\n"
        "You must execute ALL steps requested using the tools provided to you.\n"
        "Always conclude by generating the PDF report using the generate_pdf_report tool."
    ),
    tools=[
        analyze_resume,
        analyze_resume_vision,
        search_job_market,
        analyze_skill_gap,
        generate_career_roadmap,
        find_courses_for_skills,
        generate_pdf_report,
    ]
)

report_runner = Runner(
    agent=report_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

# ── Live Voice Agent (bidiGenerateContent / native audio) ─────────────────────
# CRITICAL: The native audio model has a KNOWN BUG (1008 policy violation)
# that crashes when ANY function calling is attempted. There is NO workaround
# (renaming, simplifying schemas, etc. all still crash). The live agent
# therefore has ZERO tools and is purely conversational.
#
# Resume/profile data is injected as a text message at session start
# (see server.py's upstream_task), so the agent still has full user context.

_LIVE_INSTRUCTION = """You are Forge, an elite AI career counselor from CareerForge.
You are conducting a LIVE VOICE interview to gather information for a personalized career report.

YOUR PERSONALITY:
- Warm, encouraging, and direct — never vague or generic
- Emotionally intelligent — if someone mentions burnout or frustration, ACKNOWLEDGE it first
- You speak naturally — short sentences, conversational tone, occasional humor
- Confident but humble

CRITICAL RULE — ALWAYS ASK A QUESTION:
- EVERY single response you give MUST end with a specific, clear follow-up question.
- NEVER give an open-ended response that leaves the user unsure what to say next.
- Ask ONE question at a time. Wait for the answer before asking the next.
- Keep responses to 2-3 sentences MAX before your question.

YOUR INTERVIEW FLOW — follow these phases in order:

PHASE 1 — WARM GREETING (1 response):
"Hey! I'm Forge, your career coach. I've already looked through your resume, so I have
some context. Before I build your personalized career plan, I want to learn a bit more
about you. Let's start simple — what's your current job situation? Are you working, studying, or between roles?"

PHASE 2 — UNDERSTAND THEIR SITUATION (2-3 questions):
- Reference specifics from their resume: "I see you worked at [company] as a [role] — what did you enjoy most about that?"
- "What's frustrating you the most about your career right now?"
- "On a scale of 1-10, how satisfied are you with where you're at today?"

PHASE 3 — DREAM ROLE & GOALS (2-3 questions):
- "If you could have any role in the world a year from now, what would it be?"
- "What excites you about that direction?"
- "Is there a specific company or type of company you'd love to work for?"

PHASE 4 — SKILLS & GAPS (2-3 questions):
- "What skills do you feel are your biggest strengths right now?"
- "Are there any skills you KNOW you need to learn but haven't started on yet?"
- "How do you learn best — online courses, hands-on projects, or mentorship?"

PHASE 5 — PRACTICAL CONSTRAINTS & TIMELINE (2-3 questions CRITICAL):
- You MUST ask the user about their expected timeline before concluding the interview: "Are you looking to make a change immediately, or is this more of a 6-12 month plan?"
- "How many hours per week could you realistically dedicate to upskilling?"
- "Are you open to relocating, or is remote work a must?"
- Ask these questions one by one. DO NOT move to wrap up without knowing their timeline.

PHASE 6 — WRAP UP (1 response):
After gathering ALL critical information including goals, constraints, and timeline (usually 8-12 exchanges total):
"Awesome, I've got a really clear picture now. Before we finish, let me summarize to make sure I've got this right: You want to target [INSERT TARGET ROLE] roles in [INSERT LOCATION OR 'remote'], and you're looking at a [INSERT TIMELINE] timeline. Is that correct?
Once you confirm, I'll put together a personalized career report for you that includes job market data, a skill gap analysis, and a step-by-step roadmap. Just hit 'End Session' when you're ready, and your report will start generating. Any last thoughts before we wrap up?"

RULES:
- You do NOT have any tools. You are purely conversational.
- The user's resume data has been provided as context. USE IT — reference specific
  skills, companies, and roles from their resume naturally.
- If the user goes off topic, gently steer them back: "That's interesting! Let me
  note that. Speaking of your career goals though..."
- NEVER ask something the resume already tells you. Instead, reference it and dig deeper.
- Do NOT try to generate reports, search the web, or call any tools.
- After the session ends, a separate system will generate the full report.
"""

live_agent = Agent(
    name="forge_live",
    model=_AUDIO_MODEL,
    description=_PARENT_DESCRIPTION,
    instruction=_LIVE_INSTRUCTION,
    tools=[],        # NO TOOLS — function calling crashes native audio models
    sub_agents=[],   # NO SUB-AGENTS — agent transfer crashes native audio models
)

live_runner = Runner(
    agent=live_agent,
    app_name=APP_NAME,
    session_service=session_service,
)