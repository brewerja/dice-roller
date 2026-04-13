import asyncio
import json
import os
import re
import secrets
import time
from contextlib import asynccontextmanager

import nh3
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

ROLL_PATTERN = re.compile(r"^d\d{1,10}(?:,d\d{1,10}){0,9}$")

redis_client: aioredis.Redis = None
pubsub: aioredis.client.PubSub = None


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            await pubsub.subscribe(f"room:{room_id}")
        self.rooms[room_id].add(websocket)

    async def disconnect(self, room_id: str, websocket: WebSocket):
        room = self.rooms.get(room_id, set())
        room.discard(websocket)
        if not room:
            self.rooms.pop(room_id, None)
            await pubsub.unsubscribe(f"room:{room_id}")

    async def broadcast_local(self, room_id: str, message: str):
        async def try_send(ws):
            try:
                await ws.send_text(message)
                return None
            except Exception:
                return ws

        results = await asyncio.gather(
            *[try_send(ws) for ws in self.rooms.get(room_id, set())]
        )
        for ws in results:
            if ws is not None:
                self.rooms.get(room_id, set()).discard(ws)


manager = ConnectionManager()


async def redis_listener():
    async for message in pubsub.listen():
        if message["type"] == "message":
            room_id = message["channel"].decode().removeprefix("room:")
            asyncio.create_task(manager.broadcast_local(room_id, message["data"].decode()))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, pubsub
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        redis_client = aioredis.from_url(redis_url)
    else:
        host = os.environ.get("REDISHOST", "localhost")
        port = int(os.environ.get("REDISPORT", 6379))
        password = os.environ.get("REDISPASSWORD")
        redis_client = aioredis.Redis(host=host, port=port, password=password)
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe("__init__")
    asyncio.create_task(redis_listener())
    yield
    await pubsub.aclose()
    await redis_client.aclose()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room(request: Request, room_id: str):
    return templates.TemplateResponse("room.html", {"request": request, "room_id": room_id})


@app.get("/rooms/{room_id}/rolls")
async def get_rolls(room_id: str):
    raw = await redis_client.zrange(room_id, -100, -1)
    return [json.loads(r) for r in raw]


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            name = nh3.clean(str(data.get("name", "")))
            request = nh3.clean(str(data.get("request", "")))

            if request == "ping":
                await websocket.send_text('{"pong":true}')
                continue

            results = None
            if ROLL_PATTERN.match(request):
                results = [
                    secrets.randbelow(int(part[1:])) + 1
                    for part in request.split(",")
                ]

            roll = {
                "roomId": room_id,
                "name": name,
                "timestamp": int(time.time() * 1000),
                "request": request,
                "results": results,
            }
            payload = json.dumps(roll)
            await redis_client.zadd(room_id, {payload: roll["timestamp"]})
            await redis_client.publish(f"room:{room_id}", payload)
    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)
