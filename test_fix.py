"""
Demonstrates two fixes for "site locking up and not showing current rolls":

Fix 1 (redis_listener): asyncio.create_task() so the listener isn't blocked
        while broadcasting to one room — it can process the next Redis message
        immediately.

Fix 2 (broadcast_local): asyncio.gather() sends to all clients in a room
        concurrently — a slow client no longer delays fast clients.

Each test simulates a slow WebSocket (2s send delay) alongside a fast one.
"""
import asyncio
import time


class MockWebSocket:
    def __init__(self, name, delay=0):
        self.name = name
        self.delay = delay
        self.received: list[tuple[str, float]] = []

    async def send_text(self, message):
        if self.delay:
            await asyncio.sleep(self.delay)
        self.received.append((message, time.monotonic()))


# ── Old broadcast_local (sequential sends) ───────────────────────────────────

class ConnectionManagerOld:
    def __init__(self):
        self.rooms: dict[str, set] = {}

    async def broadcast_local(self, room_id: str, message: str):
        dead = set()
        for ws in self.rooms.get(room_id, set()):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.rooms.get(room_id, set()).discard(ws)


# ── New broadcast_local (concurrent sends via asyncio.gather) ─────────────────

class ConnectionManagerNew:
    def __init__(self):
        self.rooms: dict[str, set] = {}

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


def make_room(manager):
    slow_ws = MockWebSocket("slow", delay=2.0)
    fast_ws = MockWebSocket("fast", delay=0)
    # Use an ordered list so iteration order is deterministic: slow first.
    manager.rooms["room1"] = [slow_ws, fast_ws]
    return slow_ws, fast_ws


# ── Test 1: Fix 2 alone — broadcast_local sends concurrently ─────────────────

async def test_fix2_concurrent_sends():
    """
    Within a single broadcast, a slow client must not delay a fast client.
    Old (sequential): fast_ws waits 2s for slow_ws to finish first.
    New (gather):     fast_ws gets the message immediately.
    """
    print("\n[Test 1] broadcast_local: concurrent sends (Fix 2)")

    # Old: sequential
    mgr_old = ConnectionManagerOld()
    slow, fast = make_room(mgr_old)
    start = time.monotonic()
    await mgr_old.broadcast_local("room1", "roll_1")
    fast_delay_old = fast.received[0][1] - start
    print(f"  OLD sequential: fast_ws got message at {fast_delay_old:.2f}s")

    # New: concurrent
    mgr_new = ConnectionManagerNew()
    slow, fast = make_room(mgr_new)
    start = time.monotonic()
    await mgr_new.broadcast_local("room1", "roll_1")
    fast_delay_new = fast.received[0][1] - start
    print(f"  NEW concurrent: fast_ws got message at {fast_delay_new:.2f}s")

    assert fast_delay_old > 1.9, f"Expected old to block, got {fast_delay_old:.2f}s"
    assert fast_delay_new < 0.1, f"Expected new to be instant, got {fast_delay_new:.2f}s"
    print("  PASS")


# ── Test 2: Fix 1 alone — listener doesn't block on the next Redis message ────

async def test_fix1_listener_nonblocking():
    """
    The listener publishes two messages to the same room.
    Old (await):       listener waits for broadcast 1 to finish before starting broadcast 2.
    New (create_task): listener fires both broadcasts immediately; they run concurrently.
    """
    print("\n[Test 2] redis_listener: non-blocking dispatch (Fix 1)")

    # We use the new concurrent broadcast_local for both cases so that we're
    # isolating the listener's behavior, not the within-broadcast ordering.
    async def run(use_create_task: bool):
        mgr = ConnectionManagerNew()
        slow_ws = MockWebSocket("slow", delay=2.0)
        fast_ws = MockWebSocket("fast", delay=0)
        mgr.rooms["room1"] = [slow_ws, fast_ws]

        start = time.monotonic()
        messages = [("room1", "roll_1"), ("room1", "roll_2")]

        if use_create_task:
            tasks = [asyncio.create_task(mgr.broadcast_local(r, m)) for r, m in messages]
            await asyncio.gather(*tasks)
        else:
            for room_id, payload in messages:
                await mgr.broadcast_local(room_id, payload)

        return fast_ws

    fast_old = await run(use_create_task=False)
    t_roll2_old = fast_old.received[1][1] - fast_old.received[0][1]
    print(f"  OLD (await):       gap between roll_1 and roll_2 delivery: {t_roll2_old:.2f}s")

    fast_new = await run(use_create_task=True)
    t_roll2_new = fast_new.received[1][1] - fast_new.received[0][1]
    print(f"  NEW (create_task): gap between roll_1 and roll_2 delivery: {t_roll2_new:.2f}s")

    # Old: roll_1 takes 2s (slow_ws), then roll_2 starts → gap ≥ 2s.
    # New: both start concurrently → gap ≈ 0s.
    assert t_roll2_old > 1.9, f"Expected old gap ≥ 2s, got {t_roll2_old:.2f}s"
    assert t_roll2_new < 0.1, f"Expected new gap ≈ 0s, got {t_roll2_new:.2f}s"
    print("  PASS")


async def main():
    print("=" * 60)
    print("Verifying fixes for: site locking up / rolls not showing")
    print("=" * 60)
    await test_fix2_concurrent_sends()
    await test_fix1_listener_nonblocking()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")


asyncio.run(main())
