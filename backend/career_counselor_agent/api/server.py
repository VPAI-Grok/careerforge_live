"""
CareerForge Live — FastAPI Server
Exposes the ADK runner over HTTP + WebSocket so the React frontend can talk
to Forge via text chat, file uploads, PDF downloads, and real-time voice.
"""
from __future__ import annotations

import career_counselor_agent.config  # MUST BE FIRST to setup env/API keys

import asyncio
import base64
import json
import logging
import uuid
import os
import warnings

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.genai import types
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.runners import RunConfig
from pydantic import BaseModel, Field
import io

# Suppress Pydantic serialization warnings for live streaming
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# Import the ADK runner and session service from the agent module
from career_counselor_agent.agent import runner, report_runner, live_runner, session_service, APP_NAME, live_agent
from career_counselor_agent.models import UserProfile, build_profile_context

# Diagnostic: print which tools the live agent is using
logger.info("=== LIVE AGENT DIAGNOSTIC ===")
logger.info("Live agent model: %s", live_agent.model)
for t in (live_agent.tools or []):
    fname = getattr(t, '__name__', str(t))
    logger.info("  Tool: %s (module: %s)", fname, getattr(t, '__module__', '?'))
logger.info("Sub-agents: %s", [sa.name for sa in (live_agent.sub_agents or [])])
logger.info("=== END DIAGNOSTIC ===")

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CareerForge Live API",
    description="AI career counseling powered by Google ADK + Gemini",
    version="2.0.0",
)

# Build CORS origins — localhost for dev + deployed frontend URL from env
_cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
]
# Add deployed frontend URL from environment variable (set by deploy.sh)
_frontend_url = os.environ.get("FRONTEND_URL", "")
if _frontend_url:
    _cors_origins.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── In-memory storage for session data ────────────────────────────────────────
# Stores generated PDFs and plan data per session
_session_data: dict[str, dict] = {}


# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "user_01"


class ChatResponse(BaseModel):
    session_id: str
    response: str
    user_id: str


class ResumeUploadResponse(BaseModel):
    session_id: str
    message: str
    resume_data: dict | None = None


class ProfileSubmitRequest(BaseModel):
    """Full user profile from the onboarding questionnaire."""
    session_id: str | None = None
    user_id: str = "user_01"

    # Career Context
    current_role: str = ""
    industry: str = ""
    years_experience: int = 0
    education_level: str = ""

    # Emotional & Satisfaction
    satisfaction_level: int = Field(default=5, ge=1, le=10)
    burnout_level: int = Field(default=3, ge=1, le=10)
    confidence_level: int = Field(default=5, ge=1, le=10)
    pain_points: list[str] = Field(default_factory=list)

    # Goals & Aspirations
    dream_roles: list[str] = Field(default_factory=list)
    motivation: list[str] = Field(default_factory=list)
    leadership_vs_ic: str = "Both"
    timeline: str = "1 year"

    # Skills
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    has_portfolio: bool = False

    # Work Preferences
    work_style: str = "Hybrid"
    company_size_preference: str = "No preference"
    deal_breakers: list[str] = Field(default_factory=list)

    # Location
    location: str = ""
    willing_to_relocate: bool = False

    # Financial Context
    current_salary: int | None = None
    target_salary: int | None = None
    savings_months: int | None = None
    obligations: list[str] = Field(default_factory=list)

    # Risk & Learning
    risk_tolerance: int = Field(default=5, ge=1, le=10)
    learning_hours_per_week: int = 5


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "agent": "forge", "version": "3.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Text-based chat with Forge — the main conversational endpoint."""
    session_id = req.session_id or str(uuid.uuid4())

    # Create a new session if it doesn't exist yet
    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=req.user_id,
        session_id=session_id,
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )

    # Inject profile context into the message if this session has a profile
    message_text = req.message
    session_info = _session_data.get(session_id, {})
    profile_ctx = session_info.get("profile_context")
    if profile_ctx and session_info.get("profile_injected") is not True:
        message_text = f"{profile_ctx}\n\nUser says: {req.message}"
        _session_data[session_id]["profile_injected"] = True

    # Build the ADK Content object from the plain-text message
    content = types.Content(
        role="user",
        parts=[types.Part(text=message_text)],
    )

    try:
        response_parts: list[str] = []
        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_parts.append(part.text)

            # Capture PDF data if the agent generated one
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_response and hasattr(part.function_response, "response"):
                        resp = part.function_response.response
                        if isinstance(resp, dict) and "file_base64" in resp:
                            if session_id not in _session_data:
                                _session_data[session_id] = {}
                            _session_data[session_id]["pdf"] = resp

        response_text = (
            "".join(response_parts)
            if response_parts
            else "I'm sorry, I couldn't generate a response. Could you try again?"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        user_id=req.user_id,
    )


class GenerateReportRequest(BaseModel):
    session_id: str
    user_id: str = "user_01"


from career_counselor_agent.tools.search_market import search_job_market
from career_counselor_agent.tools.skill_gap import analyze_skill_gap
from career_counselor_agent.tools.roadmap import generate_career_roadmap
from career_counselor_agent.tools.courses import find_courses_for_skills
from career_counselor_agent.tools.pdf_generator import generate_pdf_report
from google import genai

@app.post("/generate-report")
async def generate_report(req: GenerateReportRequest):
    """
    Called after a live session ends. Replaces the slow agent ADK loop with a fast,
    deterministic python sequence: Extract data -> Run tools -> Generate Markdown & PDF.
    """
    session_id = req.session_id
    user_id = req.user_id

    # Add a short delay to allow the WebSocket to finish appending the final "Wrap Up" sentences 
    # to the _session_data transcript before we begin extraction.
    await asyncio.sleep(2.0)

    session_info = _session_data.get(session_id, {})
    transcripts = session_info.get("transcripts", [])
    resume_parsed = session_info.get("resume_parsed", {})

    prompt_lines = [
        "The live voice interview has concluded. The user provided the following information during the session:\n",
    ]

    if transcripts:
        prompt_lines.append("--- INTERVIEW TRANSCRIPT ---")
        for turn in transcripts:
            role = turn.get("role", "user")  # 'user' or 'model'
            text = turn.get("text", "")
            if text.strip():
                prompt_lines.append(f"{role.capitalize()}: {text}")
        prompt_lines.append("----------------------------\n")
    else:
        prompt_lines.append("(No transcript recorded.)\n")

    if resume_parsed:
        prompt_lines.append(f"Parsed Resume Data:\n{json.dumps(resume_parsed, indent=2)}\n")

    full_prompt = "\n".join(prompt_lines)
    logger.info("Generating FAST report for session=%s", session_id)

    client = genai.Client()

    try:
        # 1. Fast Extraction
        extraction_prompt = full_prompt + """\n
CRITICAL INSTRUCTION: The transcript above may ONLY contain the AI Counselor's side of the conversation (labeled 'Model:'). 
You MUST INFER the user's selected target role, location, timeline, and complete user profile by reading the Counselor's acknowledgments and the summary in the 'WRAP UP' phase. 
For example, if the Counselor says 'AI product development sounds great' or summarizes 'You want to target AI product development', the target role is 'AI product development' (NOT their previous title from the resume). 
Only rely on the Resume Data if the user's goals cannot be inferred from the Counselor's conversational context at all.

Extract these parameters and a rich user profile from the conversation. If a profile field (like burnout_level, preferences, or salary) isn't mentioned, omit the key or use a sensible default based on the tone.
Return exactly this JSON format:
{
  "target_role": "str",
  "location": "str",
  "current_skills": ["str"],
  "timeline_months": 6,
  "user_profile": {
    "risk_tolerance": 5, "burnout_level": 3, "satisfaction_level": 5, "confidence_level": 5,
    "savings_months": 3, "obligations": ["mortgage", "kids"], "current_salary": 80000,
    "target_salary": 100000, "motivation": ["money", "growth"], "leadership_vs_ic": "IC",
    "work_style": "Remote", "company_size_preference": "Startup", "deal_breakers": ["long commute"],
    "pain_points": ["boredom"], "learning_hours_per_week": 10, "has_portfolio": false
  }
}"""
        
        extract_resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=extraction_prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        parsed = json.loads(extract_resp.text)
        target_role = parsed.get("target_role", "Software Engineer")
        location = parsed.get("location", "")
        current_skills = parsed.get("current_skills", [])
        timeline_months = parsed.get("timeline_months", 6)
        user_profile = parsed.get("user_profile", {})
        
        logger.info("Extracted: role=%s, location=%s", target_role, location)

        # 2. Run Tools Deterministically
        market_data = await search_job_market(target_role, location, user_profile=user_profile)
        logger.info("Market data pulled.")
        
        skill_gaps = await analyze_skill_gap(current_skills, target_role, market_data)
        logger.info("Skill gaps analyzed.")
        
        roadmap = await generate_career_roadmap(skill_gaps, target_role, timeline_months, user_profile=user_profile)
        logger.info("Roadmap generated.")
        
        missing = skill_gaps.get("missing_skills", [])
        courses = await find_courses_for_skills(missing)
        logger.info("Courses found.")
        
        plan_data = {
            "target_role": target_role,
            "market_data": market_data,
            "skill_gaps": skill_gaps,
            "roadmap": roadmap,
            "recommended_courses": courses
        }
        
        # 3. Final Markdown generation
        md_prompt = f"Write a beautifully formatted Markdown career plan using this JSON data:\n{json.dumps(plan_data)}\nDo not wrap in json blocks, just output elegant markdown with headers, bold text, and lists."
        md_resp = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=md_prompt
        )
        report_md = md_resp.text
        
        # 4. Generate PDF
        try:
            user_name = resume_parsed.get("personal_info", {}).get("name", "Career Seeker")
            if not isinstance(user_name, str):
                user_name = "Career Seeker"
            pdf_res = await asyncio.to_thread(generate_pdf_report, roadmap, user_name)
            
            if session_id not in _session_data:
                _session_data[session_id] = {}
            _session_data[session_id]["pdf"] = pdf_res
            has_pdf = True
        except Exception as pdf_exc:
            logger.error("PDF generation failed, falling back to markdown: %s", pdf_exc, exc_info=True)
            has_pdf = False
        
        return {
            "status": "success",
            "message": report_md,
            "has_pdf": has_pdf
        }
        
    except Exception as exc:
        logger.error("Error generating fast report: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
    user_id: str = Form("user_01"),
):
    """
    Upload a resume file (PDF or image) for direct vision-based extraction.
    Returns structured resume data for onboarding pre-population.
    """
    from career_counselor_agent.tools.resume import analyze_resume_vision

    session_id = session_id or str(uuid.uuid4())
    logger.info("upload-resume: session_id=%s, file=%s", session_id, file.filename)

    # Validate file type
    allowed_types = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. "
                   f"Accepted: PDF, PNG, JPEG, WebP.",
        )

    # Read and encode the file
    file_bytes = await file.read()
    file_b64 = base64.b64encode(file_bytes).decode("utf-8")

    # Directly call the vision tool for structured extraction
    try:
        resume_data = await analyze_resume_vision(file_b64, content_type)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume analysis failed: {exc}") from exc

    # Store resume data in session for later agent use
    if session_id not in _session_data:
        _session_data[session_id] = {}
    _session_data[session_id]["resume_b64"] = file_b64
    _session_data[session_id]["resume_mime"] = content_type
    _session_data[session_id]["resume_parsed"] = resume_data
    logger.info(
        "upload-resume: stored resume for session=%s, keys_in_session_data=%s",
        session_id, list(_session_data.keys()),
    )

    return {
        "session_id": session_id,
        "message": "Resume analyzed successfully.",
        "resume_data": resume_data,
    }



@app.get("/download-pdf/{session_id}")
async def download_pdf(session_id: str):
    """Download the generated career roadmap PDF for a session."""
    data = _session_data.get(session_id, {})
    pdf_data = data.get("pdf")
    if not pdf_data:
        raise HTTPException(
            status_code=404,
            detail="No PDF has been generated for this session yet. "
                   "Complete your career coaching session first.",
        )

    pdf_bytes = base64.b64decode(pdf_data["file_base64"])
    filename = pdf_data.get("filename", f"CareerForge_Plan_{session_id[:8]}.pdf")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.get("/session/{session_id}/plan")
async def get_session_plan(session_id: str):
    """Retrieve the generated career plan data for a session (for dashboard rendering)."""
    data = _session_data.get(session_id, {})
    plan = data.get("plan")
    if not plan:
        # Try to get it from the session events — for now return what we have
        return {
            "session_id": session_id,
            "has_plan": False,
            "message": "No plan data stored for this session yet.",
        }

    return {
        "session_id": session_id,
        "has_plan": True,
        "plan": plan,
    }


@app.post("/profile")
async def submit_profile(req: ProfileSubmitRequest):
    """
    Submit a user profile from the onboarding questionnaire.
    Creates a session and stores the profile for context injection.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # Build the UserProfile model
    profile = UserProfile(
        current_role=req.current_role,
        industry=req.industry,
        years_experience=req.years_experience,
        education_level=req.education_level,
        satisfaction_level=req.satisfaction_level,
        burnout_level=req.burnout_level,
        confidence_level=req.confidence_level,
        pain_points=req.pain_points,
        dream_roles=req.dream_roles,
        motivation=req.motivation,
        leadership_vs_ic=req.leadership_vs_ic,
        timeline=req.timeline,
        technical_skills=req.technical_skills,
        soft_skills=req.soft_skills,
        has_portfolio=req.has_portfolio,
        work_style=req.work_style,
        company_size_preference=req.company_size_preference,
        deal_breakers=req.deal_breakers,
        location=req.location,
        willing_to_relocate=req.willing_to_relocate,
        current_salary=req.current_salary,
        target_salary=req.target_salary,
        savings_months=req.savings_months,
        obligations=req.obligations,
        risk_tolerance=req.risk_tolerance,
        learning_hours_per_week=req.learning_hours_per_week,
    )

    # Generate profile context text for LLM injection
    profile_text = build_profile_context(profile)

    # Create ADK session
    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=req.user_id,
        session_id=session_id,
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )

    # Store profile in session data
    if session_id not in _session_data:
        _session_data[session_id] = {}
    _session_data[session_id]["profile"] = profile.model_dump()
    _session_data[session_id]["profile_context"] = profile_text
    _session_data[session_id]["profile_injected"] = False

    return {
        "session_id": session_id,
        "message": "Profile saved successfully. Forge is ready to coach you.",
        "profile_summary": profile_text,
    }


# ── WebSocket endpoint for real-time streaming ───────────────────────────────
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time text streaming with Forge.
    Sends partial responses as they arrive from the ADK runner.
    """
    await websocket.accept()
    user_id = "user_01"

    # Ensure session exists
    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            msg = json.loads(data)
            user_message = msg.get("message", "")

            if not user_message:
                continue

            content = types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            )

            # Stream responses back as they arrive
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            await websocket.send_json({
                                "type": "text",
                                "content": part.text,
                                "is_final": False,
                            })

            # Signal that the full response is complete
            await websocket.send_json({
                "type": "done",
                "content": "",
                "is_final": True,
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e),
            })
        except Exception:
            pass


# ── WebSocket Live Bidirectional Streaming ────────────────────────────────────
@app.websocket("/ws/live/{user_id}/{session_id}")
async def websocket_live(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
) -> None:
    """
    Live bidirectional streaming endpoint using Gemini's native audio.
    Follows the official ADK bidi-demo pattern exactly.
    """
    logger.info(
        "Live WS connection: user_id=%s, session_id=%s", user_id, session_id,
    )
    await websocket.accept()
    logger.info("Live WS accepted")

    # ── Session setup ─────────────────────────────────────────────────────
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id,
        )

    # ── RunConfig for native audio bidi streaming ─────────────────────────
    from google.adk.agents.run_config import StreamingMode, ToolThreadPoolConfig
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        # Explicitly disable audio transcription — the default
        # AudioTranscriptionConfig() is not supported by the native audio
        # model and causes 1008 (policy violation).
        output_audio_transcription=None,
        input_audio_transcription=None,
        tool_thread_pool_config=ToolThreadPoolConfig(),
    )
    logger.info("RunConfig created: %s", run_config)

    live_request_queue = LiveRequestQueue()

    # ── Build resume/profile context string (injected after connection) ────
    _context_to_inject: str | None = None
    logger.info(
        "Live WS: looking up session_id=%s in _session_data. "
        "Available keys: %s",
        session_id, list(_session_data.keys()),
    )
    session_info = _session_data.get(session_id, {})
    profile_ctx = session_info.get("profile_context")
    resume_parsed = session_info.get("resume_parsed")
    logger.info(
        "Live WS: session_info has profile_ctx=%s, resume_parsed=%s",
        bool(profile_ctx), bool(resume_parsed),
    )
    
    if profile_ctx or resume_parsed:
        context_parts = [
            "System Note: Here is the user's background context. "
            "Use this to personalize the conversation from the very start. "
            "Greet the user by name if available and reference their background naturally. "
            "Do not mention this system note to the user."
        ]
        if profile_ctx:
            context_parts.append(f"User Profile:\n{profile_ctx}")
        if resume_parsed:
            context_parts.append(
                f"Parsed Resume Data:\n{json.dumps(resume_parsed, indent=2)}"
            )
        _context_to_inject = "\n\n".join(context_parts)
        logger.info(
            "Resume/profile context prepared (%d chars), "
            "will inject after LLM connection is established.",
            len(_context_to_inject),
        )
    else:
        logger.warning(
            "Live WS: NO resume/profile context found for session_id=%s",
            session_id,
        )

    # ── Upstream: client → LiveRequestQueue ───────────────────────────────
    async def upstream_task() -> None:
        """Receives messages from WebSocket and sends to LiveRequestQueue.
        
        Also injects resume/profile context after a short delay to ensure
        the LLM bidi connection is fully established first.
        """
        logger.debug("upstream_task started")

        # Inject context AFTER the LLM connection has time to establish.
        # run_live() starts in downstream_task concurrently — it needs a
        # few seconds to open the bidi WebSocket to Gemini before we can
        # push content into the queue.
        if _context_to_inject:
            await asyncio.sleep(3)
            init_content = types.Content(
                parts=[types.Part(text=_context_to_inject)]
            )
            live_request_queue.send_content(init_content)
            logger.info("Injected resume/profile context into live session.")

        try:
            while True:
                message = await websocket.receive()

                if "bytes" in message:
                    audio_data = message["bytes"]
                    audio_blob = types.Blob(
                        mime_type="audio/pcm;rate=16000", data=audio_data,
                    )
                    live_request_queue.send_realtime(audio_blob)

                elif "text" in message:
                    text_data = message["text"]
                    try:
                        json_msg = json.loads(text_data)
                    except json.JSONDecodeError:
                        continue

                    msg_type = json_msg.get("type", "")

                    if msg_type == "text":
                        text_content = json_msg.get("text", "")
                        content = types.Content(
                            parts=[types.Part(text=text_content)],
                        )
                        live_request_queue.send_content(content)
                    elif msg_type == "close":
                        break
        except WebSocketDisconnect:
            logger.info("Client disconnected (upstream)")
        except RuntimeError as e:
            # "Cannot call receive once a disconnect message has been received"
            logger.debug("Upstream RuntimeError (normal on disconnect): %s", e)
        except Exception as e:
            logger.error("Upstream error: %s", e, exc_info=True)

    # ── Downstream: runner.run_live() → client ────────────────────────────
    if session_id not in _session_data:
        _session_data[session_id] = {}
    if "transcripts" not in _session_data[session_id]:
        _session_data[session_id]["transcripts"] = []
    _collected_transcripts = _session_data[session_id]["transcripts"]  # Collect directly to session data

    async def downstream_task() -> None:
        """Receives Events from run_live() and sends to WebSocket.
        
        Collects transcripts for post-session report generation.
        Includes auto-reconnect logic for 1008/1011 errors.
        """
        MAX_RETRIES = 3
        RETRY_DELAYS = [1.0, 2.0, 4.0]  # exponential backoff
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(
                    "downstream_task: starting run_live (attempt %d/%d)",
                    attempt + 1, MAX_RETRIES + 1,
                )
                async for event in live_runner.run_live(
                    user_id=user_id,
                    session_id=session_id,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    event_json = event.model_dump_json(
                        exclude_none=True, by_alias=True,
                    )

                    # Collect text transcripts for post-session report
                    has_audio = False
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.inline_data:
                                has_audio = True
                            elif part.text:
                                role = event.content.role or "model"
                                _collected_transcripts.append({
                                    "role": role,
                                    "text": part.text,
                                })
                    if not has_audio:
                        logger.debug("[EVENT] %s", event_json[:300])

                    await websocket.send_text(event_json)
                    
                # If run_live completes normally, break out
                logger.info("downstream_task: run_live completed normally")
                break

            except WebSocketDisconnect:
                logger.info("Client disconnected (downstream)")
                return  # Client left, don't retry

            except Exception as e:
                err_str = str(e)

                # Normal WebSocket close from Gemini — not an error
                if "1000" in err_str:
                    logger.debug("Gemini Live connection closed normally: %s", e)
                    break

                # 1008/1011 — KNOWN BUGs in native audio, auto-retry
                if "1008" in err_str or "1011" in err_str:
                    if attempt < MAX_RETRIES:
                        delay = RETRY_DELAYS[attempt]
                        logger.warning(
                            "1008 error (known native audio bug). "
                            "Auto-reconnecting in %.1fs (attempt %d/%d)...",
                            delay, attempt + 1, MAX_RETRIES,
                        )
                        # Notify frontend about reconnection
                        try:
                            reconnect_event = {
                                "content": {
                                    "role": "model",
                                    "parts": [{"text": ""}],
                                },
                                "partial": True,
                                "actions": {
                                    "customMetadata": {
                                        "type": "reconnecting",
                                        "attempt": attempt + 1,
                                        "maxRetries": MAX_RETRIES,
                                    }
                                },
                            }
                            await websocket.send_text(
                                json.dumps(reconnect_event)
                            )
                        except Exception:
                            pass  # Best-effort notification

                        await asyncio.sleep(delay)
                        continue  # Retry
                    else:
                        logger.error(
                            "1008 error persisted after %d retries. "
                            "The native audio model's function calling bug "
                            "is preventing this session from continuing.",
                            MAX_RETRIES,
                        )
                        # Notify frontend about failure
                        try:
                            error_event = {
                                "content": {
                                    "role": "model",
                                    "parts": [{"text": ""}],
                                },
                                "partial": False,
                                "actions": {
                                    "customMetadata": {
                                        "type": "error",
                                        "message": (
                                            "Voice session interrupted. "
                                            "Please reconnect."
                                        ),
                                    }
                                },
                            }
                            await websocket.send_text(
                                json.dumps(error_event)
                            )
                        except Exception:
                            pass
                        break
                else:
                    logger.error("Downstream error: %s", e, exc_info=True)
                    break

        logger.debug("downstream_task finished")

    # ── Run both tasks concurrently ───────────────────────────────────────
    try:
        logger.info("Starting live session tasks")
        up_task = asyncio.create_task(upstream_task())
        down_task = asyncio.create_task(downstream_task())
        
        done, pending = await asyncio.wait(
            [up_task, down_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        for p in pending:
            p.cancel()
    except WebSocketDisconnect:
        logger.info("Client disconnected normally")
    except asyncio.CancelledError:
        logger.info("Live WS tasks cancelled (Frontend disconnected normally).")
    except Exception as e:
        logger.error("Live session error: %s", e, exc_info=True)
    finally:
        logger.info("Cleaning up live session")
        live_request_queue.close()

        logger.info(
            "Cleaned up live session %s. Final transcript count: %d",
            session_id, len(_collected_transcripts),
        )
