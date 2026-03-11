import asyncio
from httpx import AsyncClient

async def run_test():
    async with AsyncClient() as client:
        res = await client.post("http://localhost:8000/generate-report", json={
            "session_id": "test_session_123",
            "user_id": "user_01"
        }, timeout=120)
        print("Status Code:", res.status_code)
        print("Response:", res.text)

if __name__ == "__main__":
    asyncio.run(run_test())
