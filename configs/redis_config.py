from __future__ import annotations

from typing import cast

from redis.asyncio import Redis
from redis.asyncio.client import Redis as AsyncRedis

from configs.settings import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT

_redis_client: AsyncRedis | None = None


def get_redis() -> AsyncRedis:
    global _redis_client
    if _redis_client is None:
        _redis_client = cast(
            AsyncRedis,
            Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
            ),
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
