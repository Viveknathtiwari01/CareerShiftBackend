import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    COMPETENCY_PIPELINE_VERSION,
    PIPELINE_STATUS_COMPLETED,
    PIPELINE_STATUS_FAILED,
    PIPELINE_STATUS_PENDING,
    PIPELINE_STATUS_PROCESSING,
    PIPELINE_TYPE_COMPETENCY_MAPPING,
)
from app.database.session import AsyncSessionLocal
from app.models.assessment import Assessment
from app.models.competency_mapping import CareerCompetencyMapping
from app.pipelines.context import CompetencyPipelineContext
from app.pipelines.prompt_registry import get_prompt_versions
from app.pipelines.stages import PipelineStage
from app.repositories.assessment import AssessmentRepository, assessment_repo
from app.repositories.competency_mapping import CompetencyMappingRepository, competency_mapping_repo
from app.repositories.profile import profile_repo
from app.schemas.assessment import (
    AssessmentCurrentResponse,
    AssessmentPublicResponse,
    AssessmentStartResult,
    AssessmentSummaryResponse,
)
from app.schemas.pipeline import (
    AssessmentDebugResponse,
    CompetencyItem,
    CompetencyMappingOutput,
    PipelineError,
    PipelineMetadata,
)
from app.services.competency_pipeline import CompetencyPipeline
from app.services.profile_mapper import profile_to_pipeline_input

logger = logging.getLogger(__name__)


class AssessmentService:
    def __init__(
        self,
        competency_pipeline: CompetencyPipeline,
        assessment_repository: AssessmentRepository | None = None,
        mapping_repository: CompetencyMappingRepository | None = None,
    ) -> None:
        self._pipeline = competency_pipeline
        self._assessment_repo = assessment_repository or assessment_repo
        self._mapping_repo = mapping_repository or competency_mapping_repo

    async def resolve_current_assessment(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> AssessmentCurrentResponse:
        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Complete the career assessment wizard first.",
            )

        existing, profile_stale = await self._try_resolve_existing(db, user_id, profile)
        if existing:
            return AssessmentCurrentResponse(
                assessment_id=existing.assessment_id,
                pipeline_run_id=existing.pipeline_run_id,
                status=existing.status,
                needs_sync=existing.needs_pipeline_dispatch,
                profile_stale=False,
                reused_existing=True,
            )

        return AssessmentCurrentResponse(
            needs_sync=True,
            profile_stale=profile_stale,
            reused_existing=False,
        )

    async def _try_resolve_existing(
        self,
        db: AsyncSession,
        user_id: UUID,
        profile,
    ) -> tuple[AssessmentStartResult | None, bool]:
        profile_stale_for_new = False

        active = await self._assessment_repo.get_active_for_user(
            db,
            user_id=user_id,
            pipeline_type=PIPELINE_TYPE_COMPETENCY_MAPPING,
        )
        if active and active.status == PIPELINE_STATUS_PROCESSING:
            mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=active.id)
            if mapping:
                return (
                    AssessmentStartResult(
                        assessment_id=active.id,
                        pipeline_run_id=mapping.pipeline_run_id,
                        status=active.status,
                        already_running=True,
                        needs_pipeline_dispatch=False,
                        reused_existing=True,
                    ),
                    False,
                )

        completed = await self._assessment_repo.get_latest_completed_for_user(
            db,
            user_id=user_id,
            pipeline_type=PIPELINE_TYPE_COMPETENCY_MAPPING,
        )
        if completed:
            mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=completed.id)
            if mapping:
                if not self._is_profile_stale(profile, completed, mapping):
                    return (
                        AssessmentStartResult(
                            assessment_id=completed.id,
                            pipeline_run_id=mapping.pipeline_run_id,
                            status=completed.status,
                            already_running=True,
                            needs_pipeline_dispatch=False,
                            reused_existing=True,
                            profile_stale=False,
                        ),
                        False,
                    )
                profile_stale_for_new = True

        if active:
            mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=active.id)
            if mapping:
                needs_dispatch = active.status == PIPELINE_STATUS_PENDING
                return (
                    AssessmentStartResult(
                        assessment_id=active.id,
                        pipeline_run_id=mapping.pipeline_run_id,
                        status=active.status,
                        already_running=True,
                        needs_pipeline_dispatch=needs_dispatch,
                        reused_existing=True,
                    ),
                    False,
                )

        latest = await self._assessment_repo.get_latest_for_user(
            db,
            user_id=user_id,
            pipeline_type=PIPELINE_TYPE_COMPETENCY_MAPPING,
        )
        if latest:
            mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=latest.id)
            if mapping:
                profile_stale_for_new = self._is_profile_stale(profile, latest, mapping)

                if latest.status == PIPELINE_STATUS_FAILED and not profile_stale_for_new:
                    return (
                        AssessmentStartResult(
                            assessment_id=latest.id,
                            pipeline_run_id=mapping.pipeline_run_id,
                            status=latest.status,
                            already_running=True,
                            needs_pipeline_dispatch=False,
                            reused_existing=True,
                            profile_stale=False,
                        ),
                        False,
                    )

        return None, profile_stale_for_new

    async def start_assessment(
        self,
        db: AsyncSession,
        user_id: UUID,
        *,
        force: bool = False,
    ) -> AssessmentStartResult:
        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found. Complete the career assessment wizard first.",
            )

        await self._assessment_repo.acquire_user_lock(db, user_id)

        profile_stale_for_new = False

        if not force:
            existing, profile_stale_for_new = await self._try_resolve_existing(db, user_id, profile)
            if existing:
                if existing.status == PIPELINE_STATUS_COMPLETED:
                    logger.info(
                        "Reusing completed assessment — profile unchanged",
                        extra={
                            "assessment_id": str(existing.assessment_id),
                            "user_id": str(user_id),
                        },
                    )
                elif existing.status == PIPELINE_STATUS_FAILED:
                    logger.info(
                        "Returning failed assessment for retry",
                        extra={
                            "assessment_id": str(existing.assessment_id),
                            "user_id": str(user_id),
                        },
                    )
                else:
                    logger.info(
                        "Returning in-progress assessment",
                        extra={
                            "assessment_id": str(existing.assessment_id),
                            "user_id": str(user_id),
                            "status": existing.status,
                            "needs_pipeline_dispatch": existing.needs_pipeline_dispatch,
                        },
                    )
                return existing
            if profile_stale_for_new:
                logger.info(
                    "Profile updated since last assessment — creating new run",
                    extra={"user_id": str(user_id)},
                )

        pipeline_run_id = uuid4()
        assessment = await self._assessment_repo.create(
            db,
            user_id=user_id,
            profile_id=profile.id,
            pipeline_type=PIPELINE_TYPE_COMPETENCY_MAPPING,
            status=PIPELINE_STATUS_PENDING,
        )
        await self._mapping_repo.create_for_assessment(
            db,
            assessment_id=assessment.id,
            pipeline_run_id=pipeline_run_id,
            pipeline_version=COMPETENCY_PIPELINE_VERSION,
            model_name=self._pipeline.model_name,
            prompt_versions=get_prompt_versions(),
            status=PIPELINE_STATUS_PENDING,
        )
        await db.commit()

        return AssessmentStartResult(
            assessment_id=assessment.id,
            pipeline_run_id=pipeline_run_id,
            status=PIPELINE_STATUS_PENDING,
            already_running=False,
            profile_stale=profile_stale_for_new,
            created_at=assessment.created_at,
        )

    @staticmethod
    def _is_profile_stale(
        profile,
        assessment: Assessment,
        mapping: CareerCompetencyMapping,
    ) -> bool:
        """True when the user profile changed after the last competency mapping finished."""
        if assessment.profile_id != profile.id:
            return True
        reference = mapping.completed_at or assessment.created_at
        if reference is None:
            return False
        profile_updated = profile.updated_at
        if profile_updated.tzinfo is None and reference.tzinfo is not None:
            profile_updated = profile_updated.replace(tzinfo=reference.tzinfo)
        elif profile_updated.tzinfo is not None and reference.tzinfo is None:
            reference = reference.replace(tzinfo=profile_updated.tzinfo)
        return profile_updated > reference

    async def retry_assessment(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> AssessmentStartResult:
        assessment = await self._assessment_repo.get_by_id_for_user(
            db, assessment_id=assessment_id, user_id=user_id
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")
        if assessment.status != PIPELINE_STATUS_FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed assessments can be retried.",
            )

        mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=assessment.id)
        if not mapping:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competency mapping not found.")

        new_run_id = uuid4()
        await self._mapping_repo.mark_processing(db, mapping_id=mapping.id, pipeline_run_id=new_run_id)
        await self._assessment_repo.update_status(
            db, assessment_id=assessment.id, status=PIPELINE_STATUS_PROCESSING
        )
        await db.commit()

        return AssessmentStartResult(
            assessment_id=assessment.id,
            pipeline_run_id=new_run_id,
            status=PIPELINE_STATUS_PROCESSING,
            already_running=False,
        )

    async def run_competency_pipeline(self, assessment_id: UUID) -> None:
        """Background entry point — opens its own DB session."""
        async with AsyncSessionLocal() as db:
            try:
                await self._execute_pipeline(db, assessment_id)
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.exception(
                    "Unexpected error running competency pipeline",
                    extra={"assessment_id": str(assessment_id)},
                )
                try:
                    assessment = await self._assessment_repo.get_by_id(db, assessment_id=assessment_id)
                    mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
                    if assessment and mapping and assessment.status != PIPELINE_STATUS_FAILED:
                        await self._mark_failure(
                            db,
                            assessment=assessment,
                            mapping=mapping,
                            failed_stage="pipeline_runtime",
                            error_message=str(exc)[:500],
                        )
                        await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception(
                        "Failed to persist pipeline failure state",
                        extra={"assessment_id": str(assessment_id)},
                    )

    async def _execute_pipeline(self, db: AsyncSession, assessment_id: UUID) -> None:
        assessment = await self._assessment_repo.get_by_id(db, assessment_id=assessment_id)
        if not assessment:
            logger.error("Assessment not found for pipeline run", extra={"assessment_id": str(assessment_id)})
            return

        mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
        if not mapping:
            logger.error("Mapping not found for pipeline run", extra={"assessment_id": str(assessment_id)})
            return

        profile = await profile_repo.get_by_user_id(db, assessment.user_id)
        if not profile:
            await self._mark_failure(
                db,
                assessment=assessment,
                mapping=mapping,
                failed_stage="profile_load",
                error_message="User profile not found for assessment.",
            )
            return

        await self._mapping_repo.mark_processing(
            db, mapping_id=mapping.id, pipeline_run_id=mapping.pipeline_run_id
        )
        await self._assessment_repo.update_status(
            db, assessment_id=assessment.id, status=PIPELINE_STATUS_PROCESSING
        )
        await db.commit()

        profile_data = profile_to_pipeline_input(profile)
        ctx = self._mapping_repo.build_context_from_mapping(mapping, profile_data)
        pipeline_run_id = mapping.pipeline_run_id
        ctx.assessment_id = assessment.id
        ctx.pipeline_run_id = pipeline_run_id
        ctx.model_name = self._pipeline.model_name

        async def on_stage_complete(stage: PipelineStage, output: object, duration: float) -> None:
            await self._mapping_repo.save_stage_output(
                db,
                mapping_id=mapping.id,
                stage=stage,
                output=output,
                duration=duration,
            )
            await db.commit()

        pipeline_result = await self._pipeline.execute(ctx, on_stage_complete=on_stage_complete)

        if not pipeline_result.success:
            await self._mark_failure(
                db,
                assessment=assessment,
                mapping=mapping,
                failed_stage=pipeline_result.failed_stage or "unknown",
                error_message=pipeline_result.error_message or "Pipeline stage failed.",
                total_duration=pipeline_result.total_duration_seconds,
            )
            await db.commit()
            return

        if ctx.competency_explanation is None:
            await self._mark_failure(
                db,
                assessment=assessment,
                mapping=mapping,
                failed_stage=PipelineStage.COMPETENCY_EXPLANATION.value,
                error_message="Pipeline completed without explanation output.",
                total_duration=pipeline_result.total_duration_seconds,
            )
            await db.commit()
            return

        final_output = CompetencyPipeline.assemble_final_output(ctx.competency_explanation)
        await self._mapping_repo.mark_completed(
            db,
            mapping_id=mapping.id,
            final_output=final_output,
            total_duration=pipeline_result.total_duration_seconds,
        )
        await self._assessment_repo.update_status(
            db, assessment_id=assessment.id, status=PIPELINE_STATUS_COMPLETED
        )
        await db.commit()

        logger.info(
            "Competency pipeline completed",
            extra={
                "assessment_id": str(assessment.id),
                "pipeline_run_id": str(pipeline_run_id),
                "total_duration_seconds": pipeline_result.total_duration_seconds,
            },
        )

    async def _mark_failure(
        self,
        db: AsyncSession,
        *,
        assessment: Assessment,
        mapping: CareerCompetencyMapping,
        failed_stage: str,
        error_message: str,
        total_duration: float | None = None,
    ) -> None:
        error_details = CompetencyPipeline.build_error_details(failed_stage, error_message)
        await self._mapping_repo.mark_failed(
            db,
            mapping_id=mapping.id,
            failed_stage=failed_stage,
            error_message=error_message,
            error_details=error_details,
            total_duration=total_duration,
        )
        await self._assessment_repo.update_status(
            db, assessment_id=assessment.id, status=PIPELINE_STATUS_FAILED
        )

    async def get_assessment_public(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> AssessmentPublicResponse:
        assessment, mapping = await self._get_assessment_and_mapping(db, user_id, assessment_id)
        return self._to_public_response(assessment, mapping)

    async def list_assessments_for_user(
        self,
        db: AsyncSession,
        user_id: UUID,
    ) -> list[AssessmentSummaryResponse]:
        assessments = await self._assessment_repo.list_for_user(db, user_id=user_id)
        summaries: list[AssessmentSummaryResponse] = []
        for assessment in assessments:
            mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=assessment.id)
            competency_count = None
            completed_at = None
            if mapping:
                completed_at = mapping.completed_at
                if assessment.status == PIPELINE_STATUS_COMPLETED and mapping.final_output_json:
                    competency_count = len(mapping.final_output_json.get("competencies", []))
            summaries.append(
                AssessmentSummaryResponse(
                    assessment_id=assessment.id,
                    status=assessment.status,
                    created_at=assessment.created_at,
                    completed_at=completed_at,
                    competency_count=competency_count,
                )
            )
        return summaries

    async def get_assessment_debug(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> AssessmentDebugResponse:
        assessment, mapping = await self._get_assessment_and_mapping(db, user_id, assessment_id)
        metadata = self._build_metadata(assessment, mapping)
        error = self._build_error(mapping)
        return AssessmentDebugResponse(
            assessment_id=assessment.id,
            status=assessment.status,
            role_understanding=mapping.role_understanding_json,
            competency_discovery=mapping.competency_discovery_json,
            competency_structuring=mapping.competency_structuring_json,
            competency_validation=mapping.competency_validation_json,
            competency_explanation=mapping.competency_explanation_json,
            metadata=metadata,
            error=error,
        )

    async def _get_assessment_and_mapping(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> tuple[Assessment, CareerCompetencyMapping]:
        assessment = await self._assessment_repo.get_by_id_for_user(
            db, assessment_id=assessment_id, user_id=user_id
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        mapping = await self._mapping_repo.get_by_assessment_id(db, assessment_id=assessment.id)
        if not mapping:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competency mapping not found.")

        return assessment, mapping

    def _to_public_response(
        self,
        assessment: Assessment,
        mapping: CareerCompetencyMapping,
    ) -> AssessmentPublicResponse:
        competency_mapping = None
        if assessment.status == PIPELINE_STATUS_COMPLETED and mapping.final_output_json:
            raw = mapping.final_output_json
            competencies = [
                CompetencyItem(**item) if isinstance(item, dict) else CompetencyItem.model_validate(item)
                for item in raw.get("competencies", [])
            ]
            competency_mapping = CompetencyMappingOutput(
                profession_summary=raw.get("profession_summary"),
                competencies=competencies,
            )

        return AssessmentPublicResponse(
            assessment_id=assessment.id,
            status=assessment.status,
            competency_mapping=competency_mapping,
            metadata=self._build_metadata(assessment, mapping),
            error=self._build_error_from_assessment(assessment, mapping),
        )

    def _build_metadata(
        self,
        assessment: Assessment,
        mapping: CareerCompetencyMapping,
    ) -> PipelineMetadata:
        return PipelineMetadata(
            pipeline_run_id=mapping.pipeline_run_id,
            pipeline_version=mapping.pipeline_version,
            model_name=mapping.model_name,
            started_at=mapping.started_at,
            completed_at=mapping.completed_at,
            total_duration_seconds=mapping.total_duration_seconds,
            engine_metrics=dict(mapping.engine_metrics or {}),
        )

    def _build_error(self, mapping: CareerCompetencyMapping) -> PipelineError | None:
        if mapping.status != PIPELINE_STATUS_FAILED:
            return None
        return PipelineError(
            message=mapping.error_message or "Pipeline execution failed.",
            failed_stage=mapping.failed_stage,
        )

    def _build_error_from_assessment(
        self,
        assessment: Assessment,
        mapping: CareerCompetencyMapping,
    ) -> PipelineError | None:
        if assessment.status == PIPELINE_STATUS_FAILED:
            return PipelineError(
                message=mapping.error_message or "Pipeline execution failed.",
                failed_stage=mapping.failed_stage,
            )
        return self._build_error(mapping)
