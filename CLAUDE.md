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

**Run tests:**
```bash
uv run pytest
```

## Architecture

FastAPI / Python 3.15 real-time dice-rolling app using plain WebSockets with Redis persistence.

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

**Dice notation regex:** `^d[1-9]\d{0,9}(?:,d[1-9]\d{0,9}){0,9}$`

**Environment variables:**
- `REDIS_URL` — full Redis URL (used on fly.io with Upstash)
- `REDISHOST`, `REDISPORT`, `REDISPASSWORD` — individual Redis connection params (local dev fallback)

**Security:** TLS termination handled by fly.io proxy; no HTTPS-redirect logic in the app.

## Production (Fly.io)

- Fly app `ip-dice-roller`, region `ord`, live at https://ip-dice-roller.fly.dev. Two machines; with `auto_stop_machines` one is usually `stopped`, which is normal.
- **The `main` branch auto-deploys.** Merging a PR into `main` creates a new Fly release within a few minutes. The deploys come from Fly's GitHub app (`fly-io[bot]`), whose branch is set in the Fly dashboard; there's no GitHub Actions workflow.
- The `fly` CLI needs `fly auth login` (interactive; the user runs it as `! fly auth login`).

**Checking a deploy:**
```bash
fly releases -a ip-dice-roller   # newest version should be "complete" a few minutes after merge
fly status -a ip-dice-roller     # machines should be on that version
```
- Confirm the new code from outside: `curl` the room page or `https://ip-dice-roller.fly.dev/static/dieroll.js` and grep for something from the change, or exercise a behavior over `wss://ip-dice-roller.fly.dev/ws/<room>`. Use a throwaway room name, since rolls are saved in the production Redis.
- The `Warning: Metrics token unavailable` line from `fly` commands is harmless.
- Browser tabs that were already open keep the old `dieroll.js` until they're reloaded.

**Production reads need the user's go-ahead.** `fly logs` and `fly ssh console` are blocked in auto mode unless the user asks for them. Ask the user to run them with `!`, or run them only when they explicitly request it:
```bash
fly logs -a ip-dice-roller --no-tail
fly ssh console -a ip-dice-roller -C "/app/.venv/bin/python --version"
```

**Reading the logs:**
- A healthy cold start goes from `Preparing to run: /app/.venv/bin/uvicorn ...` to `Application startup complete` in about 3 seconds, with no uv `Downloading`/`Building` lines.
- During a deploy, a few `instance refused connection` errors (requests arriving before uvicorn is listening) and `lease currently held` errors for the second machine are expected. They should stop within seconds.
- uvicorn logs WebSocket opens (`[accepted]` / `connection open`) but not closes. A tab reconnecting about every 60 seconds, often two at once, meant duplicate client sockets that Fly's proxy closed as idle; this was fixed in PR #4.
