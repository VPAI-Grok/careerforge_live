import asyncio
from google import genai
from google.genai import types

async def main():
    client = genai.Client()
    model = "gemini-2.5-flash-native-audio-preview-12-2025"
    
    print("Test 4: Adding advanced config")
    try:
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
        )
        async with client.aio.live.connect(model=model, config=config) as session:
            print("  -> SUCCESS")
    except Exception as e:
        print("  -> ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
