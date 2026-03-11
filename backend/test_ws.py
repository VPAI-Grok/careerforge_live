import asyncio
import websockets

async def test_ws():
    uri = "ws://127.0.0.1:8011/ws/live/user_01/test_123"
    try:
        async with websockets.connect(uri) as ws:
            print("Connected to FastAPI WS")
            # Wait a few seconds to see if server disconnects
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                print("Received from server:", msg)
            except asyncio.TimeoutError:
                print("No message received in 3s, connection still open!")
    except Exception as e:
        print("WS Connection failed:", repr(e))

if __name__ == "__main__":
    asyncio.run(test_ws())
