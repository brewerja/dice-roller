.PHONY: init check test build run redis

REDIS_CONTAINER = dice-redis
REDIS_PORT = 6379
REDIS_PING = uv run python -c "import redis; redis.Redis(port=$(REDIS_PORT), socket_connect_timeout=1).ping()" 2>/dev/null

init:
	uv sync

# Fixes what ruff can, then reports anything left.
check:
	uv run ruff check --fix .
	uv run ruff format .
	uv run ty check
	uv run complexipy --failed .

test:
	uv run pytest

build:
	docker build -t brewerja/dice-roller .

# Starts Redis on localhost:$(REDIS_PORT) in Docker unless something is already answering there.
redis:
	@if ! $(REDIS_PING); then \
		echo "Starting Redis container $(REDIS_CONTAINER)"; \
		docker start $(REDIS_CONTAINER) >/dev/null 2>&1 || \
			docker run -d --name $(REDIS_CONTAINER) -p $(REDIS_PORT):6379 redis >/dev/null; \
		for i in 1 2 3 4 5 6 7 8 9 10; do $(REDIS_PING) && break; sleep 0.5; done; \
		$(REDIS_PING) || { echo "Redis didn't start"; exit 1; }; \
	fi

run: redis
	REDISPORT=$(REDIS_PORT) uv run uvicorn app.main:app --reload
