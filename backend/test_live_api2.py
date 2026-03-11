import asyncio
from google import genai
from google.genai import types

async def main():
    client = genai.Client()
    model = "gemini-2.5-flash-native-audio-preview-12-2025"
    
    print("Test 1: Only Audio response modality")
    try:
        config = types.LiveConnectConfig(response_modalities=["AUDIO"])
        async with client.aio.live.connect(model=model, config=config) as session:
            print("  -> SUCCESS")
    except Exception as e:
        print("  -> ERROR:", repr(e))

    print("Test 2: Audio modality + System Instruction")
    try:
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(parts=[types.Part(text="Hello")])
        )
        async with client.aio.live.connect(model=model, config=config) as session:
            print("  -> SUCCESS")
    except Exception as e:
        print("  -> ERROR:", repr(e))

    print("Test 3: Audio modality + Tools")
    try:
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=[{"function_declarations": [{"name": "test_func", "description": "Test"}]}]
        )
        async with client.aio.live.connect(model=model, config=config) as session:
            print("  -> SUCCESS")
    except Exception as e:
        print("  -> ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
