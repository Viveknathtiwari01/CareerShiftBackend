from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.constants import (
    PIPELINE_STATUS_COMPLETED,
    PIPELINE_STATUS_FAILED,
    PIPELINE_STATUS_PENDING,
    PIPELINE_STATUS_PROCESSING,
)
from app.models.assessment import Assessment
from app.models.competency_mapping import CareerCompetencyMapping
from app.services.assessment import AssessmentService
from app.services.competency_pipeline import CompetencyPipeline


def _make_mapping(**overrides) -> CareerCompetencyMapping:
    defaults = {
        "id": uuid4(),
        "assessment_id": uuid4(),
        "pipeline_run_id": uuid4(),
        "pipeline_version": "1.0.0",
        "model_name": "claude-test",
        "engine_metrics": {},
        "prompt_versions": {},
        "status": PIPELINE_STATUS_PENDING,
    }
    defaults.update(overrides)
    mapping = CareerCompetencyMapping(**{k: v for k, v in defaults.items() if k != "id"})
    mapping.id = defaults["id"]
    return mapping


def _make_assessment(**overrides) -> Assessment:
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "profile_id": uuid4(),
        "pipeline_type": "competency_mapping",
        "status": PIPELINE_STATUS_PENDING,
    }
    defaults.update(overrides)
    assessment = Assessment(**{k: v for k, v in defaults.items() if k != "id"})
    assessment.id = defaults["id"]
    return assessment


class TestAssessmentServicePublicResponse:
    def test_public_response_excludes_stage_json(self):
        pipeline = CompetencyPipeline(engines=MagicMock())
        service = AssessmentService(competency_pipeline=pipeline)

        assessment = _make_assessment(status=PIPELINE_STATUS_COMPLETED)
        mapping = _make_mapping(
            assessment_id=assessment.id,
            status=PIPELINE_STATUS_COMPLETED,
            final_output_json={
                "profession_summary": "Summary",
                "competencies": [
                    {
                        "name": "HRIS",
                        "category": "Technical",
                        "importance": "High",
                        "expected_level": "Advanced",
                        "what_it_is": "x",
                        "why_it_matters": "y",
                        "professional_context": "z",
                    }
                ],
            },
            role_understanding_json={"profession": "secret"},
            started_at=datetime.now(timezone.utc),
        )

        response = service._to_public_response(assessment, mapping)

        assert response.status == PIPELINE_STATUS_COMPLETED
        assert response.competency_mapping is not None
        assert response.competency_mapping.profession_summary == "Summary"
        assert len(response.competency_mapping.competencies) == 1
        dumped = response.model_dump()
        assert "role_understanding_json" not in dumped
        assert "competency_discovery_json" not in dumped

    def test_failed_response_includes_error_not_stage_json(self):
        pipeline = CompetencyPipeline(engines=MagicMock())
        service = AssessmentService(competency_pipeline=pipeline)

        assessment = _make_assessment(status=PIPELINE_STATUS_FAILED)
        mapping = _make_mapping(
            assessment_id=assessment.id,
            status=PIPELINE_STATUS_FAILED,
            failed_stage="competency_structuring",
            error_message="Structuring failed",
            role_understanding_json={"profession": "kept"},
        )

        response = service._to_public_response(assessment, mapping)

        assert response.error is not None
        assert response.error.failed_stage == "competency_structuring"
        assert response.competency_mapping is None
        dumped = response.model_dump()
        assert "role_understanding" not in str(dumped)


@pytest.mark.asyncio
async def test_start_assessment_returns_existing_when_active():
    user_id = uuid4()
    assessment_id = uuid4()
    run_id = uuid4()

    assessment_repo = MagicMock()
    mapping_repo = MagicMock()
    pipeline = CompetencyPipeline(engines=MagicMock())

    active = _make_assessment(id=assessment_id, user_id=user_id, status=PIPELINE_STATUS_PROCESSING)
    mapping = _make_mapping(assessment_id=assessment_id, pipeline_run_id=run_id)

    assessment_repo.acquire_user_lock = AsyncMock()
    assessment_repo.get_active_for_user = AsyncMock(return_value=active)
    mapping_repo.get_by_assessment_id = AsyncMock(return_value=mapping)

    profile_repo_mock = MagicMock()
    profile_repo_mock.get_by_user_id = AsyncMock(return_value=MagicMock(id=uuid4()))

    service = AssessmentService(
        competency_pipeline=pipeline,
        assessment_repository=assessment_repo,
        mapping_repository=mapping_repo,
    )

    with patch("app.services.assessment.profile_repo", profile_repo_mock):
        result = await service.start_assessment(db=AsyncMock(), user_id=user_id)

    assert result.already_running is True
    assert result.assessment_id == assessment_id
    assert result.pipeline_run_id == run_id
    assessment_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_start_assessment_raises_without_profile():
    user_id = uuid4()
    assessment_repo = MagicMock()
    mapping_repo = MagicMock()
    pipeline = CompetencyPipeline(engines=MagicMock())

    assessment_repo.acquire_user_lock = AsyncMock()
    assessment_repo.get_active_for_user = AsyncMock(return_value=None)

    profile_repo_mock = MagicMock()
    profile_repo_mock.get_by_user_id = AsyncMock(return_value=None)

    service = AssessmentService(
        competency_pipeline=pipeline,
        assessment_repository=assessment_repo,
        mapping_repository=mapping_repo,
    )

    with patch("app.services.assessment.profile_repo", profile_repo_mock):
        with pytest.raises(HTTPException) as exc:
            await service.start_assessment(db=AsyncMock(), user_id=user_id)

    assert exc.value.status_code == 404
