import asyncio
from google.genai import types
from career_counselor_agent.agent import live_runner, APP_NAME, session_service
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.agents.live_request_queue import LiveRequestQueue

async def main():
    print("Testing ADK LiveRunner with text context injection...")
    await session_service.create_session(
        app_name=APP_NAME, user_id="test_user", session_id="test_session"
    )
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=types.SessionResumptionConfig(),
    )
    live_request_queue = LiveRequestQueue()
    
    # Send text context BEFORE runner starts (same as server.py)
    init_content = types.Content(
        parts=[types.Part(text="System Note: Here is some context about the user. They are an experienced engineer.")]
    )
    live_request_queue.send_content(init_content)

    try:
        async for event in live_runner.run_live(
            user_id="test_user",
            session_id="test_session",
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            print("Received event:", event)
            break
            
    except Exception as e:
        print("ADK Error:", repr(e))
        
    print("Finished.")

if __name__ == "__main__":
    asyncio.run(main())
