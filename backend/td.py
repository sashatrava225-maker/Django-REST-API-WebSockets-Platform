from fastapi import FastAPI, Depends, HTTPException, WebSocket, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

import json
import models
import schemas
from database import SessionLocal, engine


# APP
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections = set()
room_connections = {}
connection_info = {}

# DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CONFIG
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 2

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# PASSWORDS
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


# JWT
def create_token(data: dict):
    to_encode = data.copy()
    to_encode.update({
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# AUTH USER
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise credentials_exception

    return user


# ---------------- REGISTER ----------------
@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):

    existing = db.query(models.User).filter(
        models.User.username == user.username
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="User exists")

    new_user = models.User(
        username=user.username,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "created", "user_id": new_user.id}


# ---------------- LOGIN (IMPORTANT FIX) ----------------
@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = db.query(models.User).filter(
        models.User.username == form_data.username
    ).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_token({"user_id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ---------------- ITEMS ----------------
@app.post("/items", response_model=schemas.ItemResponse)
def create_item(
    item: schemas.ItemCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    db_item = models.Item(
        name=item.name,
        quantity=item.quantity,
        is_bought=False,
        user_id=current_user.id
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    background_tasks.add_task(
        broadcast,
        {"type": "update"}
    )

    return db_item

@app.get("/items", response_model=list[schemas.ItemResponse])
def get_items(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    return db.query(models.Item).filter(
        models.Item.user_id == current_user.id
    ).all()


@app.put("/items/{item_id}", response_model=schemas.ItemResponse)
def update_item(
    item_id: int,
    item_data: schemas.ItemUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    if item_data.name is not None:
        item.name = item_data.name

    if item_data.quantity is not None:
        item.quantity = item_data.quantity

    if item_data.is_bought is not None:
        item.is_bought = item_data.is_bought

    db.commit()
    db.refresh(item)

    
    background_tasks.add_task(
        broadcast,
        {"type": "update"}
    )

    return item

@app.patch("/items/{item_id}/buy")
def mark_as_bought(
    item_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    item.is_bought = True

    db.commit()
    db.refresh(item)

    # 🔥 ОЦЕ ДОДАЄМО
    background_tasks.add_task(
        broadcast,
        {"type": "update"}
    )

    return item


@app.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):

    item = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    db.delete(item)
    db.commit()

    
    background_tasks.add_task(
        broadcast,
        {"type": "update"}
    )

    return {"message": "deleted"}

async def broadcast(data: dict):

    dead = []

    for ws in active_connections:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            dead.append(ws)

    for ws in dead:
        active_connections.discard(ws)


def remove_connection(websocket: WebSocket):
    active_connections.discard(websocket)
    info = connection_info.pop(websocket, None)

    if info:
        room = info.get("room")
        if room and websocket in room_connections.get(room, set()):
            room_connections[room].discard(websocket)
            if not room_connections[room]:
                room_connections.pop(room, None)


async def broadcast_to_room(room: str, payload: dict):
    dead = []

    for ws in list(room_connections.get(room, set())):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)

    for ws in dead:
        remove_connection(ws)


def validate_room_name(room):
    if not isinstance(room, str) or not room.strip():
        return None

    room = room.strip()
    if len(room) > 100:
        return None

    return room


def validate_chat_payload(data):
    if not isinstance(data, dict):
        return None

    if data.get("type") != "chat_message":
        return None

    room = validate_room_name(data.get("room"))
    message = data.get("message")

    if not isinstance(message, str) or not message.strip():
        return None

    room = room
    message = message.strip()

    if len(message) > 2000:
        return None

    return {
        "room": room,
        "message": message,
    }


@app.websocket("/ws")
async def ws(websocket: WebSocket):

    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            await websocket.close(code=1008)
            return

    except Exception as e:
        print("JWT ERROR:", e)
        await websocket.close(code=1008)
        return

    await websocket.accept()
    active_connections.add(websocket)
    connection_info[websocket] = {
        "user_id": user_id,
        "room": None,
    }

    print("WS CONNECTED USER:", user_id)

    try:
        while True:
            raw_message = await websocket.receive_text()

            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Message must be valid JSON."
                })
                continue

            message_type = data.get("type")

            if message_type == "join_room":
                room = validate_room_name(data.get("room"))
                if not room:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid payload. Expected: {'type': 'join_room', 'room': '<room>'}"
                    })
                    continue

                previous_room = connection_info.get(websocket, {}).get("room")
                if previous_room and websocket in room_connections.get(previous_room, set()):
                    room_connections[previous_room].discard(websocket)
                    if not room_connections[previous_room]:
                        room_connections.pop(previous_room, None)

                room_connections.setdefault(room, set()).add(websocket)
                connection_info[websocket]["room"] = room
                await websocket.send_json({
                    "type": "room_joined",
                    "room": room,
                })
                continue

            if message_type == "leave_room":
                room = validate_room_name(data.get("room"))
                if not room:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid payload. Expected: {'type': 'leave_room', 'room': '<room>'}"
                    })
                    continue

                if websocket in room_connections.get(room, set()):
                    room_connections[room].discard(websocket)
                    if not room_connections[room]:
                        room_connections.pop(room, None)
                if connection_info.get(websocket):
                    connection_info[websocket]["room"] = None
                await websocket.send_json({
                    "type": "room_left",
                    "room": room,
                })
                continue

            validated = validate_chat_payload(data)
            if not validated:
                await websocket.send_json({
                    "type": "error",
                    "message": (
                        "Invalid payload. Expected: "
                        "{'type': 'chat_message', 'room': '<room>', 'message': '<text>'}"
                    )
                })
                continue

            room = validated["room"]
            message = validated["message"]

            room_connections.setdefault(room, set()).add(websocket)
            connection_info[websocket]["room"] = room

            db = SessionLocal()
            try:
                chat_message = models.ChatMessage(
                    room=room,
                    sender_id=user_id,
                    content=message,
                )
                db.add(chat_message)
                db.commit()
                db.refresh(chat_message)
            finally:
                db.close()

            await broadcast_to_room(room, {
                "type": "chat_message",
                "message_id": chat_message.id,
                "room": room,
                "user_id": user_id,
                "message": chat_message.content,
                "created_at": chat_message.created_at.isoformat() if chat_message.created_at else None,
            })

    except WebSocketDisconnect:
        print("WS DISCONNECTED")

    finally:
        remove_connection(websocket)
