import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.session import Session
from app.models.user import User
from app.services.auth import AuthService


def _make_user(**overrides) -> User:
    defaults = {
        "id": uuid.uuid4(),
        "email": "user@example.com",
        "username": "user",
        "password_hash": "hash",
        "status": "active",
    }
    defaults.update(overrides)
    user = User(**{k: v for k, v in defaults.items() if k != "id"})
    user.id = defaults["id"]
    return user


def _make_session(**overrides) -> Session:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "token_jti": "jti-123",
        "login_time": datetime.now(timezone.utc),
        "last_activity": datetime.now(timezone.utc),
        "is_revoked": False,
        "is_expired": False,
    }
    defaults.update(overrides)
    session = Session(**{k: v for k, v in defaults.items() if k != "id"})
    session.id = defaults["id"]
    return session


@pytest.mark.asyncio
async def test_refresh_tokens_returns_new_access_token():
    user = _make_user()
    session = _make_session(user_id=user.id, token_jti="jti-123")
    db = AsyncMock()
    service = AuthService(db)

    with patch("app.services.auth.SecurityService.decode_token") as decode, patch(
        "app.services.auth.session_repo.get_by_token_jti", new=AsyncMock(return_value=session)
    ), patch("app.services.auth.user_repo.get", new=AsyncMock(return_value=user)), patch(
        "app.services.auth.SecurityService.create_access_token", return_value="new-access"
    ):
        decode.return_value = {"type": "refresh", "jti": "jti-123", "sub": str(user.id)}
        result = await service.refresh_tokens("refresh-token")

    assert result.access_token == "new-access"
    assert result.refresh_token == "refresh-token"
