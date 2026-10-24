"""
One-time cleanup for rooms saved before rolls were trimmed and rooms expired.

Trims each room to its newest MAX_ROLLS_PER_ROOM rolls and sets it to expire
ROOM_TTL_SECONDS after its last roll. Rooms whose last roll is already older
than that are deleted. Prints what it would do unless run with --apply.

    python scripts/expire_old_rooms.py [--apply]
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import MAX_ROLLS_PER_ROOM, ROOM_TTL_SECONDS, create_redis_client


async def main(apply: bool):
    redis = create_redis_client()
    now = time.time()
    async for key in redis.scan_iter(_type="zset"):
        newest = await redis.zrange(key, -1, -1, withscores=True)
        if not newest:
            continue
        expires_at = int(float(newest[0][1]) / 1000) + ROOM_TTL_SECONDS
        count = await redis.zcard(key)
        extra = max(0, count - MAX_ROLLS_PER_ROOM)
        action = (
            "delete"
            if expires_at <= now
            else f"expire in {(expires_at - now) / 86400:.0f} days"
        )
        print(f"{key.decode()}: {count} rolls, trim {extra}, {action}")
        if apply:
            async with redis.pipeline() as pipe:
                pipe.zremrangebyrank(key, 0, -MAX_ROLLS_PER_ROOM - 1)
                pipe.expireat(key, expires_at)  # a time in the past deletes the key
                await pipe.execute()
    if not apply:
        print("Dry run; nothing changed. Run with --apply to make these changes.")
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
