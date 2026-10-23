"""
End-to-end tests of the real WebSocket endpoint in app/main.py, using
fakeredis in place of a Redis server.
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(monkeypatch):
    fake = fakeredis.FakeAsyncRedis()
    monkeypatch.setattr(main, "redis_client", fake)
    monkeypatch.setattr(main, "pubsub", fake.pubsub(ignore_subscribe_messages=True))
    monkeypatch.setattr(main, "manager", main.ConnectionManager())
    with TestClient(main.app) as client:
        yield client


def roll(ws, request):
    ws.send_json({"name": "Tester", "request": request})
    return ws.receive_json()


def test_roll(client):
    with client.websocket_connect("/ws/room1") as ws:
        result = roll(ws, "d6,d6")
    assert result["request"] == "d6,d6"
    assert len(result["results"]) == 2
    assert all(1 <= n <= 6 for n in result["results"])


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
