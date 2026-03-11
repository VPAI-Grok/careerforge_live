import asyncio
import os
import sys
from google import genai
from google.genai import types

async def test_live(model_name):
    print(f"\n--- Testing {model_name} ---")
    client = genai.Client()
    try:
        async with client.aio.live.connect(model=model_name) as session:
            print("Connected without config!")
            
        config = types.LiveConnectConfig(
            system_instruction=types.Content(parts=[types.Part(text="Hello")]),
            tools=[{"function_declarations": [{"name": "test_func", "description": "Test"}]}]
        )
        async with client.aio.live.connect(model=model_name, config=config) as session:
            print("Connected WITH tools and system_instruction!")
    except Exception as e:
        print("ERROR:", repr(e))

async def main():
    models = [
        "gemini-2.5-flash-native-audio-preview-12-2025",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-2.5-flash"
    ]
    for m in models:
        await test_live(m)

if __name__ == "__main__":
    asyncio.run(main())
