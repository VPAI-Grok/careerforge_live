"""
Test: Force tool execution during live session.
If this crashes with 1008, the issue is function_response handling.
"""
import asyncio, os

if 'GEMINI_API_KEY' in os.environ:
    del os.environ['GEMINI_API_KEY']

from dotenv import load_dotenv
load_dotenv('career_counselor_agent/.env', override=True)

from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.runners import RunConfig
from google.adk.agents.run_config import StreamingMode

ss = InMemorySessionService()

# A tool that actually DOES something and returns data
async def search_jobs(role: str, location: str = "") -> str:
    """Searches for job market data for a given role."""
    import json
    # Simulate what search_job_market returns
    return json.dumps({
        "role": role,
        "salary": {"min": 80000, "max": 150000},
        "demand": "high",
        "top_employers": ["Google", "Meta", "Amazon"],
    })

agent = Agent(
    name="test",
    model="gemini-2.5-flash-native-audio-preview-12-2025",
    description="Test",
    instruction="You are a career advisor. When the user asks about jobs, ALWAYS call the search_jobs tool first.",
    tools=[search_jobs],
)

runner = Runner(agent=agent, app_name="test", session_service=ss)

async def main():
    await ss.create_session(app_name="test", user_id="u1", session_id="s1")
    lrq = LiveRequestQueue()
    rc = RunConfig(response_modalities=["AUDIO"], streaming_mode=StreamingMode.BIDI)
    
    # Ask something that FORCES tool execution
    lrq.send_content(types.Content(parts=[types.Part(text="Search for Python developer jobs in New York. Use the search_jobs tool.")]))
    
    print("Waiting for events (tool should execute)...")
    try:
        event_count = 0
        async def get_events():
            nonlocal event_count
            async for event in runner.run_live(
                user_id="u1", session_id="s1",
                live_request_queue=lrq, run_config=rc,
            ):
                event_count += 1
                # Print interesting events
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            print(f"  FUNCTION CALL: {part.function_call.name}({part.function_call.args})")
                        if hasattr(part, 'function_response') and part.function_response:
                            print(f"  FUNCTION RESPONSE received by model")
                        if part.text:
                            print(f"  TEXT: {part.text[:100]}")
                if event_count % 20 == 0:
                    print(f"  ... {event_count} events so far")
        
        await asyncio.wait_for(get_events(), timeout=15.0)
    except asyncio.TimeoutError:
        print(f"SUCCESS — {event_count} events, tool executed OK!")
    except Exception as e:
        print(f"ERROR after {event_count} events: {repr(e)}")

asyncio.run(main())
