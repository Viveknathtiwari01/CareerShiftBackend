from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.constants import PIPELINE_STATUS_PROCESSING
from app.models.assessment import Assessment
from app.models.competency_mapping import CareerCompetencyMapping
from app.services.assessment import AssessmentService
from app.services.competency_pipeline import CompetencyPipeline


def _make_assessment(**overrides) -> Assessment:
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "profile_id": uuid4(),
        "pipeline_type": "competency_mapping",
        "status": PIPELINE_STATUS_PROCESSING,
    }
    defaults.update(overrides)
    assessment = Assessment(**{k: v for k, v in defaults.items() if k != "id"})
    assessment.id = defaults["id"]
    return assessment


def _make_mapping(**overrides) -> CareerCompetencyMapping:
    defaults = {
        "id": uuid4(),
        "assessment_id": uuid4(),
        "pipeline_run_id": uuid4(),
        "pipeline_version": "1.0.0",
        "model_name": "claude-test",
        "engine_metrics": {},
        "prompt_versions": {},
        "status": PIPELINE_STATUS_PROCESSING,
        "started_at": datetime.now(timezone.utc) - timedelta(minutes=30),
    }
    defaults.update(overrides)
    mapping = CareerCompetencyMapping(**{k: v for k, v in defaults.items() if k != "id"})
    mapping.id = defaults["id"]
    return mapping


@pytest.mark.asyncio
async def test_recover_stale_processing_marks_failed():
    pipeline = CompetencyPipeline(engines=MagicMock())
    service = AssessmentService(competency_pipeline=pipeline)
    db = AsyncMock()

    assessment = _make_assessment()
    mapping = _make_mapping(
        assessment_id=assessment.id,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    service._mapping_repo.get_by_assessment_id = AsyncMock(return_value=mapping)
    service._mark_failure = AsyncMock()

    with patch("app.services.assessment.settings") as mock_settings:
        mock_settings.PIPELINE_STALE_AFTER_SECONDS = 900
        recovered = await service._recover_stale_processing(db, assessment)

    assert recovered is True
    service._mark_failure.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_flow_sequence_is_documented():
    """Smoke test: submit orchestration endpoints exist in API modules."""
    from app.api.v1.assessment import analysis_routes
    from app.api.v1.assessment import report_routes

    analysis_paths = {route.path for route in analysis_routes.router.routes}
    report_paths = {route.path for route in report_routes.router.routes}

    assert "/{assessment_id}/analyze" in analysis_paths
    assert "/{assessment_id}/generate-report" in report_paths
