"""Tests for AI readiness service wiring."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.ai_readiness import AIReadinessService


@pytest.mark.asyncio
async def test_get_readiness_requires_completed_assessment():
    service = AIReadinessService()
    db = AsyncMock()
    user_id = uuid4()
    assessment_id = uuid4()

    assessment = MagicMock()
    assessment.status = "PROCESSING"

    with patch(
        "app.services.ai_readiness.assessment_repo.get_by_id_for_user",
        new=AsyncMock(return_value=assessment),
    ):
        with pytest.raises(HTTPException) as exc:
            await service.get_readiness(db, user_id, assessment_id)

    assert exc.value.status_code == 400


def test_readiness_route_is_registered():
    from app.api.v1.assessment import readiness_routes

    paths = {route.path for route in readiness_routes.router.routes}
    assert "/{assessment_id}/readiness" in paths
