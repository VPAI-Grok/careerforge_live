import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from career_counselor_agent.api.server import generate_report, GenerateReportRequest

async def main():
    req = GenerateReportRequest(session_id="test_session_123", user_id="user_01")
    try:
        res = await generate_report(req)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
