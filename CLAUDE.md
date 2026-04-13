# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run locally** (requires Redis):
```bash
docker run --rm -d -p 6379:6379 redis
uv run uvicorn app.main:app --reload
```
App runs on `http://localhost:8000`.

**Install dependencies:**
```bash
uv sync
```

**Build Docker image:**
```bash
docker build -t brewerja/dice-roller .
```

There are no tests in this project.

## Architecture

FastAPI / Python 3.12 real-time dice-rolling app using plain WebSockets with Redis persistence.

**Request flow:**
1. Browser loads `templates/room.html` (Jinja2) at `GET /rooms/{room_id}`
2. `static/dieroll.js` connects via native WebSocket to `/ws/{room_id}`
3. Roll requests are sent as JSON `{name, request}` over the WebSocket
4. `app/main.py` validates format, rolls dice with `secrets.randbelow()`, sanitizes with `nh3.clean()`, persists to Redis sorted set, and broadcasts to all room subscribers
5. Roll history loaded on page load via `GET /rooms/{room_id}/rolls` (returns last 100 rolls)

**Key files:**
- `app/main.py` — all WebSocket and REST endpoints, ConnectionManager, roll logic
- `static/dieroll.js` — native WebSocket client, keyboard shortcuts (R=d6+d6, B=d20, G=d6)
- `templates/room.html` — Jinja2 template for the room page
- `static/index.html` — landing page
- `pyproject.toml` — Python dependencies (fastapi, uvicorn, redis, jinja2, nh3)

**Dice notation regex:** `^d\d{1,10}(?:,d\d{1,10}){0,9}$`

**Environment variables:**
- `REDIS_URL` — full Redis URL (used on fly.io with Upstash)
- `REDISHOST`, `REDISPORT`, `REDISPASSWORD` — individual Redis connection params (local dev fallback)

**Security:** TLS termination handled by fly.io proxy; no HTTPS-redirect logic in the app.
