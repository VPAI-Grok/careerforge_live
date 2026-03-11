from google.genai.live import AsyncLive
from google.genai import types
import json

class FakeClient:
    vertexai = False

class FakeAsyncLive(AsyncLive):
    def __init__(self):
        self._api_client = FakeClient()

live = FakeAsyncLive()
r = types.FunctionResponse(id='abc', name='test', response={'foo':'bar'})
c = types.Content(parts=[types.Part(function_response=r)])
msg = live._parse_client_message(c)
print('Final Message Keys:', msg.keys())
print(json.dumps(msg))
