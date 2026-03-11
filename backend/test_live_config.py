"""
Diagnostic: reproduce the EXACT server flow and capture the LiveConnectConfig.
"""
import asyncio
import os
import sys
import pathlib
import json

# Load the env same way agent.py does
from dotenv import load_dotenv
env_path = pathlib.Path("career_counselor_agent/.env")
load_dotenv(env_path)

# Remove GEMINI_API_KEY to avoid conflicts
if "GEMINI_API_KEY" in os.environ:
    del os.environ["GEMINI_API_KEY"]
    print("Removed GEMINI_API_KEY from environ")

print(f"GOOGLE_API_KEY set: {'GOOGLE_API_KEY' in os.environ}")

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.agents.live_request_queue import LiveRequestQueue

# Import the live agent
from career_counselor_agent.agent import live_agent, APP_NAME


async def main():
    session_service = InMemorySessionService()
    live_runner = Runner(
        agent=live_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name=APP_NAME, user_id="test_user"
    )

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        output_audio_transcription=None,
        input_audio_transcription=None,
    )

    live_request_queue = LiveRequestQueue()

    print(f"\n=== RunConfig ===")
    print(f"  response_modalities: {run_config.response_modalities}")
    print(f"  output_audio_transcription: {run_config.output_audio_transcription}")
    print(f"  input_audio_transcription: {run_config.input_audio_transcription}")
    print(f"  session_resumption: {run_config.session_resumption}")

    # Monkey-patch the live API connect to capture the config
    from google.genai import _api_client
    original_connect = None
    
    from google.genai.live import AsyncLive
    original_connect_method = AsyncLive.connect

    captured_config = {}

    def patched_connect(self_live, *, model, config):
        print(f"\n=== CAPTURED LiveConnectConfig ===")
        print(f"  Model: {model}")
        # Print the config as dict, excluding huge fields
        try:
            config_dict = config.model_dump(exclude_none=True)
            # Don't print system_instruction (too long)
            if 'system_instruction' in config_dict:
                config_dict['system_instruction'] = '<TRUNCATED>'
            # Print tools summary
            if 'tools' in config_dict:
                for i, tool in enumerate(config_dict['tools']):
                    if 'function_declarations' in tool:
                        names = [fd['name'] for fd in tool['function_declarations']]
                        tool['function_declarations'] = f"[{len(names)} funcs: {', '.join(names)}]"
                    if 'google_search' in tool:
                        print(f"  *** FOUND google_search IN TOOLS! ***")
                    if 'google_search_retrieval' in tool:
                        print(f"  *** FOUND google_search_retrieval IN TOOLS! ***")
                    if 'code_execution' in tool:
                        print(f"  *** FOUND code_execution IN TOOLS! ***")
            print(f"  Config: {json.dumps(config_dict, indent=2, default=str)}")
        except Exception as e:
            print(f"  Error dumping config: {e}")
            print(f"  Raw config: {config}")
        
        captured_config['config'] = config
        captured_config['model'] = model
        return original_connect_method(self_live, model=model, config=config)

    AsyncLive.connect = patched_connect

    print("\n=== Starting live session... ===")
    
    try:
        async for event in live_runner.run_live(
            session=session,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"  [TEXT] {part.text[:100]}")
                    if part.function_call:
                        print(f"  [FUNC_CALL] {part.function_call.name}({part.function_call.args})")
                    if part.inline_data:
                        print(f"  [AUDIO] {len(part.inline_data.data)} bytes")
            
            # After receiving a couple events, close
            await asyncio.sleep(0.1)
            
    except Exception as e:
        print(f"\n=== ERROR: {type(e).__name__}: {e} ===")
    finally:
        # Restore
        AsyncLive.connect = original_connect_method
        print("\n=== Done ===")
        
        # Save exact dumped config to file
        if 'config' in captured_config:
            try:
                out = captured_config['config'].model_dump(exclude_none=True)
                if 'system_instruction' in out:
                    out['system_instruction'] = '<TRUNCATED>'
                with open("live_config_dump.json", "w") as f:
                    json.dump(out, f, indent=2, default=str)
                print("Dumped config to live_config_dump.json")
            except Exception as e:
                print(f"Failed to dump: {e}")


if __name__ == "__main__":
    asyncio.run(main())
