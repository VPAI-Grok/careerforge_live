import asyncio
import os
from google import genai
from google.genai import types
from google.adk.agents.live_request_queue import LiveRequestQueue

async def main():
    queue = LiveRequestQueue()
    
    # ADK simulates this in __build_response_event
    function_response = types.FunctionResponse(
        id="test_id_123",
        name="test_function",
        response={"result": "success"}
    )
    part = types.Part(function_response=function_response)
    content = types.Content(parts=[part])
    
    queue.send_content(content)
    req = await queue.get()
    
    from google.genai._live_converters import _Content_to_mldev
    try:
        to_object = {}
        parsed = _Content_to_mldev(content, to_object)
        
        # also process using model_dump to compare with Pydantic serialization
        print(f"Content_to_mldev Output: {parsed}")
        
        import json
        try:
            print("Dict JSON Dumps:", json.dumps(parsed))
        except Exception as e:
            print("JSON Dumps Error:", e)
    except Exception as e:
        print("Error details:", e)

if __name__ == "__main__":
    asyncio.run(main())
