# brewerja/dice-roller

Simple app to have chat/dice-rolling rooms.

Live at: https://ip-dice-roller.fly.dev/

### Run locally (requires Docker for Redis):

```bash
docker run --rm -d -p 6379:6379 redis
uv run uvicorn app.main:app --reload
```

App runs on `http://localhost:8000`.

### Build the image:

```bash
docker build -t brewerja/dice-roller .
```

### Run a container:

```bash
docker run -p 8000:8000 brewerja/dice-roller
```
