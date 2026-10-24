"""
End-to-end tests of the real WebSocket endpoint in app/main.py, using
fakeredis in place of a Redis server.
"""

import asyncio
import time

import fakeredis
import pytest
import redis
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


def test_favicon(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.content.startswith(b"\x00\x00\x01\x00")  # .ico header


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
    async def broken_zadd(*args, **kwargs):
        raise RuntimeError("Redis is down")

    monkeypatch.setattr(main.redis_client, "zadd", broken_zadd)
    with pytest.raises(RuntimeError), client.websocket_connect("/ws/room1") as ws:
        ws.send_json({"name": "Tester", "request": "d6"})
        ws.receive_json()
    assert "room1" not in main.manager.rooms


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
