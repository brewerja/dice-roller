"""
End-to-end tests of the real WebSocket endpoint in app/main.py, using
fakeredis in place of a Redis server.
"""

import asyncio
import hashlib
import time
from typing import cast

import fakeredis
import pytest
import redis
from fastapi import WebSocket
from fastapi.testclient import TestClient
from redis.asyncio.connection import AbstractConnection

from app import main


@pytest.fixture
def fake_redis(monkeypatch):
    fake = fakeredis.FakeAsyncRedis()
    monkeypatch.setattr(main, "redis_client", fake)
    monkeypatch.setattr(main, "pubsub", fake.pubsub(ignore_subscribe_messages=True))
    monkeypatch.setattr(main, "manager", main.ConnectionManager())


@pytest.fixture
def client(fake_redis):
    with TestClient(main.app) as client:
        yield client


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "/rooms/" in response.text


def test_index_page_lists_rooms_newest_first(client, monkeypatch):
    for i, room_id in enumerate(["old", "new <b>&"]):
        monkeypatch.setattr(main.time, "time", lambda i=i: 1_700_000_000.0 + i)
        with client.websocket_connect(f"/ws/{room_id}") as ws:
            roll(ws, "d6")
    text = client.get("/").text
    assert "new &lt;b&gt;&amp;</a>" in text
    new_href = 'href="/rooms/new%20%3Cb%3E%26"'
    assert text.index(new_href) < text.index('href="/rooms/old"')


def test_index_page_with_no_rooms(client):
    assert "No rooms yet." in client.get("/").text


def test_room_page_versions_its_script(client):
    response = client.get("/rooms/room1")
    with open("static/dieroll.js", "rb") as f:
        version = hashlib.sha256(f.read()).hexdigest()[:12]
    assert f'src="/static/dieroll.js?v={version}"' in response.text


def test_favicon(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.content.startswith(b"\x00\x00\x01\x00")  # .ico header


class FakeSocket:
    def __init__(self, delay=0.0, fail=False):
        self.delay = delay
        self.fail = fail
        self.received: list[tuple[str, float]] = []

    async def send_text(self, message):
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("socket closed")
        self.received.append((message, time.monotonic()))


def put_in_room(*sockets: FakeSocket):
    main.manager.rooms["room1"] = cast(set[WebSocket], set(sockets))


def roll(ws, request):
    ws.send_json({"name": "Tester", "request": request})
    return ws.receive_json()


def test_roll(client):
    with client.websocket_connect("/ws/room1") as ws:
        result = roll(ws, "d6,d6")
    assert result["request"] == "d6,d6"
    assert len(result["results"]) == 2
    assert all(1 <= n <= 6 for n in result["results"])


def test_same_millisecond_rolls_are_kept_apart(client, monkeypatch):
    # Same player, same roll, same result, same millisecond: without an ID the
    # two payloads would be identical and Redis would store them as one.
    monkeypatch.setattr(main.time, "time", lambda: 1_700_000_000.0)
    monkeypatch.setattr(main.secrets, "randbelow", lambda n: 0)
    with client.websocket_connect("/ws/room1") as ws:
        first = roll(ws, "d6")
        second = roll(ws, "d6")
    assert first["timestamp"] == second["timestamp"]
    assert first["id"] != second["id"]
    assert len(client.get("/rooms/room1/rolls").json()) == 2


def test_heartbeat_gets_pong(client):
    with client.websocket_connect("/ws/room1") as ws:
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"pong": True}
    assert client.get("/rooms/room1/rolls").json() == []


def test_player_can_say_ping(client):
    with client.websocket_connect("/ws/room1") as ws:
        ws.send_json({"name": "", "request": "ping"})
        result = ws.receive_json()
    assert result["request"] == "ping"


def test_long_messages_are_cut_off(client):
    with client.websocket_connect("/ws/room1") as ws:
        ws.send_json({"name": "n" * 600, "request": "m" * 600})
        result = ws.receive_json()
    assert result["name"] == "n" * main.MAX_MESSAGE_CHARS
    assert result["request"] == "m" * main.MAX_MESSAGE_CHARS


def test_images_are_removed(client):
    with client.websocket_connect("/ws/room1") as ws:
        ws.send_json(
            {
                "name": '<img src="x.png">Tester',
                "request": '<b>hi</b> <img src="x.png">',
            }
        )
        result = ws.receive_json()
    assert result["name"] == "Tester"
    assert result["request"] == "<b>hi</b> "


def test_room_keeps_only_newest_rolls(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_ROLLS_PER_ROOM", 3)
    clock = iter(range(1_700_000_000, 1_700_000_100))
    monkeypatch.setattr(main.time, "time", lambda: next(clock))
    with client.websocket_connect("/ws/room1") as ws:
        for i in range(5):
            roll(ws, f"message {i}")
    rolls = client.get("/rooms/room1/rolls").json()
    assert [r["request"] for r in rolls] == ["message 2", "message 3", "message 4"]


def test_room_expires_after_no_rolls(client):
    with client.websocket_connect("/ws/room1") as ws:
        roll(ws, "d6")
    ttl = client.portal.call(main.redis_client.ttl, "room1")
    assert main.ROOM_TTL_SECONDS - 5 < ttl <= main.ROOM_TTL_SECONDS


def test_d0_is_chat_and_keeps_connection(client):
    with client.websocket_connect("/ws/room1") as ws:
        result = roll(ws, "d0")
        assert result["request"] == "d0"
        assert result["results"] is None

        result = roll(ws, "d20")
        assert len(result["results"]) == 1


def test_invalid_json_keeps_connection(client):
    with client.websocket_connect("/ws/room1") as ws:
        ws.send_text("not json")
        ws.send_text('["a", "list"]')
        result = roll(ws, "d6")
        assert len(result["results"]) == 1


def test_room_cleaned_up_after_disconnect(client):
    with client.websocket_connect("/ws/room1") as ws:
        roll(ws, "d6")
        assert "room1" in main.manager.rooms
    assert "room1" not in main.manager.rooms


def test_room_cleaned_up_after_unexpected_error(client, monkeypatch):
    async def broken_publish(*args, **kwargs):
        raise RuntimeError("Redis is down")

    monkeypatch.setattr(main.redis_client, "publish", broken_publish)
    with pytest.raises(RuntimeError), client.websocket_connect("/ws/room1") as ws:
        ws.send_json({"name": "Tester", "request": "d6"})
        ws.receive_json()
    assert "room1" not in main.manager.rooms


def test_room_gets_live_rolls_after_subscribe_fails(client, monkeypatch):
    subscribe = main.pubsub.subscribe

    async def fail_once(*args, **kwargs):
        monkeypatch.setattr(main.pubsub, "subscribe", subscribe)
        raise redis.ConnectionError("Redis is down")

    monkeypatch.setattr(main.pubsub, "subscribe", fail_once)
    with pytest.raises(redis.ConnectionError), client.websocket_connect("/ws/room1"):
        pass
    with client.websocket_connect("/ws/room1") as ws:
        result = roll(ws, "d6")
    assert result["request"] == "d6"


def test_listener_recovers_after_redis_error(fake_redis, monkeypatch):
    monkeypatch.setattr(main, "LISTENER_RETRY_SECONDS", 0.01)
    real_get_message = main.pubsub.get_message
    failures = []

    async def get_message_failing_once(*args, **kwargs):
        if not failures:
            failures.append(True)
            raise redis.ConnectionError("Connection closed by server.")
        return await real_get_message(*args, **kwargs)

    monkeypatch.setattr(main.pubsub, "get_message", get_message_failing_once)
    with TestClient(main.app) as client, client.websocket_connect("/ws/room1") as ws:
        result = roll(ws, "d6")
    assert failures
    assert len(result["results"]) == 1


def test_listener_reconnects_when_pubsub_goes_silent(fake_redis, monkeypatch):
    # Simulate a connection that died without an error: nothing arrives, not
    # even ping replies, until the listener drops the connection.
    monkeypatch.setattr(main, "LISTENER_RETRY_SECONDS", 0.01)
    monkeypatch.setattr(main, "PUBSUB_PING_SECONDS", 0.01)
    monkeypatch.setattr(main, "PUBSUB_TIMEOUT_SECONDS", 0.05)
    real_get_message = main.pubsub.get_message
    real_disconnect = AbstractConnection.disconnect
    silent = [True]
    disconnects = []

    async def get_message(*args, **kwargs):
        if silent[0]:
            await asyncio.sleep(kwargs.get("timeout") or 0)
            return None
        return await real_get_message(*args, **kwargs)

    async def disconnect(self, *args, **kwargs):
        disconnects.append(kwargs)
        silent[0] = False
        return await real_disconnect(self, *args, **kwargs)

    monkeypatch.setattr(main.pubsub, "get_message", get_message)
    monkeypatch.setattr(AbstractConnection, "disconnect", disconnect)
    with TestClient(main.app) as client, client.websocket_connect("/ws/room1") as ws:
        # Rolls published while the connection is dead are lost, so wait for the
        # listener to notice and reconnect before rolling.
        deadline = time.monotonic() + 5
        while not disconnects and time.monotonic() < deadline:
            time.sleep(0.01)
        assert disconnects, "listener never noticed the silent connection"
        time.sleep(0.2)
        result = roll(ws, "d6")
    assert len(result["results"]) == 1


async def test_slow_socket_does_not_delay_others(fake_redis):
    slow, fast = FakeSocket(delay=0.5), FakeSocket()
    put_in_room(slow, fast)
    start = time.monotonic()
    await main.manager.broadcast_local("room1", "roll")
    assert fast.received[0][1] - start < 0.1


async def test_dead_socket_is_dropped_from_room(fake_redis):
    dead, alive = FakeSocket(fail=True), FakeSocket()
    put_in_room(dead, alive)
    await main.manager.broadcast_local("room1", "roll")
    assert main.manager.rooms["room1"] == {alive}
    assert [m for m, _ in alive.received] == ["roll"]


def test_listener_does_not_wait_for_slow_broadcasts(client):
    # Each message's broadcast takes 1s because of the slow socket. The listener
    # must hand off broadcasts without waiting, so the fast socket gets both rolls
    # well before that.
    slow, fast = FakeSocket(delay=1.0), FakeSocket()
    client.portal.call(main.pubsub.subscribe, "room:room1")
    put_in_room(slow, fast)
    client.portal.call(main.redis_client.publish, "room:room1", "roll 1")
    client.portal.call(main.redis_client.publish, "room:room1", "roll 2")
    deadline = time.monotonic() + 0.8
    while len(fast.received) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert [m for m, _ in fast.received] == ["roll 1", "roll 2"]
