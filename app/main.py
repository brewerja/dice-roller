import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import cast

import nh3
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

ROLL_PATTERN = re.compile(r"^d[1-9]\d{0,9}(?:,d[1-9]\d{0,9}){0,9}$")
# Longer names and messages are cut off at this many characters.
MAX_MESSAGE_CHARS = 500
# HTML tags allowed in names and messages: nh3's defaults, minus images.
ALLOWED_TAGS = nh3.ALLOWED_TAGS - {"img"}
# Each room keeps only its newest rolls, and is deleted after this long with no rolls.
MAX_ROLLS_PER_ROOM = 1000
ROOM_TTL_SECONDS = 30 * 24 * 60 * 60
LISTENER_RETRY_SECONDS = 1.0
# Fail Redis commands and connection attempts instead of waiting forever on a dead connection.
REDIS_TIMEOUT_SECONDS = 10
# Ping the pub/sub connection when it's been quiet this long, and reconnect if
# nothing at all (not even the ping's reply) has arrived in PUBSUB_TIMEOUT_SECONDS.
PUBSUB_PING_SECONDS = 30
PUBSUB_TIMEOUT_SECONDS = 75

logger = logging.getLogger("uvicorn.error")


def create_redis_client() -> aioredis.Redis:
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        return aioredis.from_url(
            redis_url,
            socket_timeout=REDIS_TIMEOUT_SECONDS,
            socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
        )
    return aioredis.Redis(
        host=os.environ.get("REDISHOST", "localhost"),
        port=int(os.environ.get("REDISPORT", "6379")),
        password=os.environ.get("REDISPASSWORD"),
        socket_timeout=REDIS_TIMEOUT_SECONDS,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
    )


# Neither connects until first use, so it's safe to create them at import time.
redis_client = create_redis_client()
pubsub = redis_client.pubsub(ignore_subscribe_messages=True)


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        # Record the room only once it's subscribed. Otherwise a failed subscribe
        # would leave the room looking subscribed, and it would never get live rolls.
        if room_id not in self.rooms:
            await pubsub.subscribe(f"room:{room_id}")
        self.rooms.setdefault(room_id, set()).add(websocket)

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
            except Exception:  # noqa: BLE001 - any send failure means the socket is dead
                return ws

        results = await asyncio.gather(
            *[try_send(ws) for ws in self.rooms.get(room_id, set())]
        )
        for ws in results:
            if ws is not None:
                self.rooms.get(room_id, set()).discard(ws)


manager = ConnectionManager()


# asyncio only keeps weak references to tasks, so hold them until they finish.
background_tasks: set[asyncio.Task] = set()


def run_in_background(coro):
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


async def listen_for_rolls():
    # pubsub.listen() would block forever on a connection that died silently, so
    # read with a timeout and ping when it's quiet to confirm Redis is still there.
    last_heard = time.monotonic()
    while True:
        message = await pubsub.get_message(timeout=PUBSUB_PING_SECONDS)
        if message is not None:
            last_heard = time.monotonic()
            if message["type"] == "message":
                room_id = message["channel"].decode().removeprefix("room:")
                run_in_background(
                    manager.broadcast_local(room_id, message["data"].decode())
                )
        elif time.monotonic() - last_heard > PUBSUB_TIMEOUT_SECONDS:
            # The next get_message() reconnects and resubscribes to every room.
            if pubsub.connection:
                await pubsub.connection.disconnect(nowait=True)
            raise aioredis.ConnectionError(
                f"No reply from Redis pub/sub in {PUBSUB_TIMEOUT_SECONDS}s"
            )
        else:
            await pubsub.ping()


async def redis_listener():
    # redis-py reconnects and resubscribes on its own after a brief drop, but gives
    # up after a few retries. Keep listening for the life of the app regardless.
    while True:
        try:
            await listen_for_rolls()
        except Exception:
            logger.exception(
                "Redis listener failed; retrying in %ss", LISTENER_RETRY_SECONDS
            )
        await asyncio.sleep(LISTENER_RETRY_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await pubsub.subscribe("__init__")
    listener = asyncio.create_task(redis_listener())
    yield
    listener.cancel()
    with suppress(asyncio.CancelledError):
        await listener
    await pubsub.aclose()
    await redis_client.aclose()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse("static/index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")


@app.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room(request: Request, room_id: str):
    # The script's URL changes whenever the script does, so browsers can't keep
    # using a cached old copy with a newer page.
    script_version = hashlib.sha256(Path("static/dieroll.js").read_bytes()).hexdigest()[
        :12
    ]
    return templates.TemplateResponse(
        request, "room.html", {"room_id": room_id, "script_version": script_version}
    )


@app.get("/rooms/{room_id}/rolls")
async def get_rolls(room_id: str):
    raw = cast(list[bytes], await redis_client.zrange(room_id, -100, -1))
    return [json.loads(r) for r in raw]


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                continue  # not valid JSON; ignore it and keep the connection
            if not isinstance(data, dict):
                continue
            if data.get("type") == "ping":
                await websocket.send_text('{"pong":true}')
                continue
            name = nh3.clean(
                str(data.get("name", ""))[:MAX_MESSAGE_CHARS], tags=ALLOWED_TAGS
            )
            request = nh3.clean(
                str(data.get("request", ""))[:MAX_MESSAGE_CHARS], tags=ALLOWED_TAGS
            )

            results = None
            if ROLL_PATTERN.match(request):
                results = [
                    secrets.randbelow(int(part[1:])) + 1 for part in request.split(",")
                ]

            roll = {
                "id": secrets.token_hex(8),
                "roomId": room_id,
                "name": name,
                "timestamp": int(time.time() * 1000),
                "request": request,
                "results": results,
            }
            payload = json.dumps(roll)
            async with redis_client.pipeline() as pipe:
                pipe.zadd(room_id, {payload: roll["timestamp"]})
                pipe.zremrangebyrank(room_id, 0, -MAX_ROLLS_PER_ROOM - 1)
                pipe.expire(room_id, ROOM_TTL_SECONDS)
                await pipe.execute()
            await redis_client.publish(f"room:{room_id}", payload)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(room_id, websocket)
