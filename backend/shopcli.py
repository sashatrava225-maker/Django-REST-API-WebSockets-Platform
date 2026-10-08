import asyncio
import websockets
import json

BASE_WS = "ws://localhost:8000/ws"


async def send(ws, data):
    await ws.send(json.dumps(data))


async def cli():
    async with websockets.connect(BASE_WS) as ws:

        print("CLI connected to WebSocket")

        while True:
            print("\n1. Add item")
            print("2. Delete item")
            print("0. Exit")

            choice = input("Choose: ")

            if choice == "1":
                name = input("Name: ")

                await send(ws, {
                    "action": "add",
                    "name": name,
                    "quantity": 1
                })

            elif choice == "2":
                item_id = int(input("ID: "))

                await send(ws, {
                    "action": "delete",
                    "id": item_id
                })

            elif choice == "0":
                break

            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1)
                print("STATE UPDATE:", msg)
            except:
                pass


asyncio.run(cli())
