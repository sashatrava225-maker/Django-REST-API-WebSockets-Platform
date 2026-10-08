from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import json

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

clients = {}  # user_id -> websocket


def get_user_id(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except JWTError:
        return None


async def broadcast_user_state(user_id: int):
    db = SessionLocal()

    items = db.query(models.Item).filter(
        models.Item.user_id == user_id
    ).all()

    state = [{
        "id": i.id,
        "name": i.name,
        "quantity": i.quantity,
        "is_bought": i.is_bought
    } for i in items]

    db.close()

    ws = clients.get(user_id)
    if ws:
        await ws.send_text(json.dumps({
            "type": "state",
            "items": state
        }))


async def handle_ws(websocket: WebSocket, token: str):
    await websocket.accept()

    user_id = get_user_id(token)
    if not user_id:
        await websocket.close()
        return

    clients[user_id] = websocket

    await broadcast_user_state(user_id)

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)

            db = SessionLocal()

            if data["action"] == "add":
                item = models.Item(
                    name=data["name"],
                    quantity=data.get("quantity", 1),
                    user_id=user_id
                )
                db.add(item)
                db.commit()

            elif data["action"] == "delete":
                item = db.query(models.Item).filter(
                    models.Item.id == data["id"],
                    models.Item.user_id == user_id
                ).first()

                if item:
                    db.delete(item)
                    db.commit()

            db.close()

            await broadcast_user_state(user_id)

    except WebSocketDisconnect:
        clients.pop(user_id, None)
