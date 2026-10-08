import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ItemsConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()

        await self.send(text_data=json.dumps({
            "event": "connected",
            "message": "WebSocket is live 🔥"
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)

        await self.send(text_data=json.dumps({
            "event": "echo",
            "you_sent": data
        }))
