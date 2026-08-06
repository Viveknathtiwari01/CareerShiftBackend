import pytest
from fastapi import HTTPException

from app.core.rate_limit import enforce_rate_limit, reset_rate_limits


@pytest.fixture(autouse=True)
def _clear_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.mark.asyncio
async def test_rate_limit_allows_requests_under_limit():
    for _ in range(3):
        await enforce_rate_limit("test:user", limit=3, window_seconds=60, label="tests")


@pytest.mark.asyncio
async def test_rate_limit_blocks_when_exceeded():
    for _ in range(2):
        await enforce_rate_limit("test:block", limit=2, window_seconds=60, label="tests")

    with pytest.raises(HTTPException) as exc:
        await enforce_rate_limit("test:block", limit=2, window_seconds=60, label="tests")

    assert exc.value.status_code == 429
    assert "Rate limit exceeded" in exc.value.detail


@pytest.mark.asyncio
async def test_rate_limit_keys_are_isolated():
    await enforce_rate_limit("user:a", limit=1, window_seconds=60, label="tests")
    await enforce_rate_limit("user:b", limit=1, window_seconds=60, label="tests")

    with pytest.raises(HTTPException):
        await enforce_rate_limit("user:a", limit=1, window_seconds=60, label="tests")
