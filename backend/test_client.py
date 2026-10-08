import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8765") as ws:
        print("Connected!")

        await ws.send(json.dumps({
            "action": "add",
            "item": "apple"
        }))

        while True:
            msg = await ws.recv()
            print("Got:", msg)

asyncio.run(test())
