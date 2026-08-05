from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    PIPELINE_STATUS_COMPLETED,
    PIPELINE_STATUS_FAILED,
    PIPELINE_STATUS_PROCESSING,
    PIPELINE_STATUS_PENDING,
)
from app.models.competency_mapping import CareerCompetencyMapping
from app.pipelines.context import CompetencyPipelineContext
from app.pipelines.stages import STAGE_JSON_COLUMNS, PipelineStage


class CompetencyMappingRepository:
    async def create_for_assessment(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
        pipeline_run_id: UUID,
        pipeline_version: str,
        model_name: str,
        prompt_versions: dict[str, str],
        status: str = PIPELINE_STATUS_PENDING,
    ) -> CareerCompetencyMapping:
        mapping = CareerCompetencyMapping(
            assessment_id=assessment_id,
            pipeline_run_id=pipeline_run_id,
            pipeline_version=pipeline_version,
            model_name=model_name,
            prompt_versions=prompt_versions,
            status=status,
            engine_metrics={},
        )
        db.add(mapping)
        await db.flush()
        await db.refresh(mapping)
        return mapping

    async def get_by_assessment_id(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> Optional[CareerCompetencyMapping]:
        result = await db.execute(
            select(CareerCompetencyMapping).where(
                CareerCompetencyMapping.assessment_id == assessment_id,
                CareerCompetencyMapping.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().first()

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        mapping_id: UUID,
    ) -> Optional[CareerCompetencyMapping]:
        result = await db.execute(
            select(CareerCompetencyMapping).where(
                CareerCompetencyMapping.id == mapping_id,
                CareerCompetencyMapping.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().first()

    async def mark_processing(
        self,
        db: AsyncSession,
        *,
        mapping_id: UUID,
        pipeline_run_id: UUID,
        started_at: datetime | None = None,
    ) -> None:
        mapping = await self.get_by_id(db, mapping_id=mapping_id)
        if not mapping:
            return
        mapping.status = PIPELINE_STATUS_PROCESSING
        mapping.pipeline_run_id = pipeline_run_id
        mapping.started_at = started_at or datetime.now(timezone.utc)
        mapping.failed_stage = None
        mapping.error_message = None
        mapping.error_details = None
        db.add(mapping)
        await db.flush()

    async def save_stage_output(
        self,
        db: AsyncSession,
        *,
        mapping_id: UUID,
        stage: PipelineStage,
        output: Any,
        duration: float,
    ) -> None:
        mapping = await self.get_by_id(db, mapping_id=mapping_id)
        if not mapping:
            return

        column_name = STAGE_JSON_COLUMNS[stage]
        current_value = getattr(mapping, column_name)
        if current_value is not None:
            return

        setattr(mapping, column_name, output)
        metrics = dict(mapping.engine_metrics or {})
        metrics[stage.value] = duration
        mapping.engine_metrics = metrics
        db.add(mapping)
        await db.flush()

    async def mark_completed(
        self,
        db: AsyncSession,
        *,
        mapping_id: UUID,
        final_output: dict[str, Any],
        completed_at: datetime | None = None,
        total_duration: float | None = None,
    ) -> None:
        mapping = await self.get_by_id(db, mapping_id=mapping_id)
        if not mapping:
            return
        mapping.status = PIPELINE_STATUS_COMPLETED
        mapping.final_output_json = final_output
        mapping.completed_at = completed_at or datetime.now(timezone.utc)
        mapping.total_duration_seconds = total_duration
        mapping.failed_stage = None
        mapping.error_message = None
        mapping.error_details = None
        db.add(mapping)
        await db.flush()

    async def mark_failed(
        self,
        db: AsyncSession,
        *,
        mapping_id: UUID,
        failed_stage: str,
        error_message: str,
        error_details: dict[str, Any] | None = None,
        completed_at: datetime | None = None,
        total_duration: float | None = None,
    ) -> None:
        mapping = await self.get_by_id(db, mapping_id=mapping_id)
        if not mapping:
            return
        mapping.status = PIPELINE_STATUS_FAILED
        mapping.failed_stage = failed_stage
        mapping.error_message = error_message
        mapping.error_details = error_details
        mapping.completed_at = completed_at or datetime.now(timezone.utc)
        if total_duration is not None:
            mapping.total_duration_seconds = total_duration
        db.add(mapping)
        await db.flush()

    def build_context_from_mapping(
        self,
        mapping: CareerCompetencyMapping,
        profile: dict[str, Any],
    ) -> CompetencyPipelineContext:
        return CompetencyPipelineContext(
            profile=profile,
            role_understanding=mapping.role_understanding_json,
            competency_discovery=mapping.competency_discovery_json,
            competency_structuring=mapping.competency_structuring_json,
            competency_validation=mapping.competency_validation_json,
            competency_explanation=mapping.competency_explanation_json,
            assessment_id=mapping.assessment_id,
            pipeline_run_id=mapping.pipeline_run_id,
            model_name=mapping.model_name,
        )


competency_mapping_repo = CompetencyMappingRepository()
