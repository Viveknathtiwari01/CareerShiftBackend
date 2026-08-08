"""In-memory sliding-window rate limiter for single-instance deployments."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, status

from app.core.config import settings

_lock = asyncio.Lock()
_buckets: dict[str, Deque[float]] = defaultdict(deque)


async def enforce_rate_limit(
    key: str,
    *,
    limit: int | None = None,
    window_seconds: int | None = None,
    label: str = "requests",
) -> None:
    max_requests = limit if limit is not None else 5
    window = window_seconds if window_seconds is not None else 3600
    now = time.monotonic()

    async with _lock:
        bucket = _buckets[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {label}. Try again later.",
            )
        bucket.append(now)


def reset_rate_limits() -> None:
    _buckets.clear()
