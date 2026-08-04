import hashlib
import traceback
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.core.constants import COMPETENCY_PIPELINE_VERSION
from app.pipelines.base_pipeline import BasePipeline, PipelineExecutionResult, PipelineStageResult
from app.pipelines.context import CompetencyPipelineContext
from app.pipelines.engine_protocol import EngineRunFn
from app.pipelines.stages import COMPETENCY_PIPELINE_STAGES, PipelineStage

StagePersistCallback = Callable[
    [PipelineStage, Any, float],
    Awaitable[None],
]


@dataclass
class CompetencyPipelineEngines:
    role_understanding: EngineRunFn
    competency_discovery: EngineRunFn
    competency_structuring: EngineRunFn
    competency_validation: EngineRunFn
    competency_explanation: EngineRunFn

    @classmethod
    def default(cls) -> "CompetencyPipelineEngines":
        from services import (
            competency_discovery,
            competency_explanation,
            competency_structuring,
            competency_validation,
            role_understanding,
        )

        return cls(
            role_understanding=role_understanding.run,
            competency_discovery=competency_discovery.run,
            competency_structuring=competency_structuring.run,
            competency_validation=competency_validation.run,
            competency_explanation=competency_explanation.run,
        )

    def get_engine(self, stage: PipelineStage) -> EngineRunFn:
        return {
            PipelineStage.ROLE_UNDERSTANDING: self.role_understanding,
            PipelineStage.COMPETENCY_DISCOVERY: self.competency_discovery,
            PipelineStage.COMPETENCY_STRUCTURING: self.competency_structuring,
            PipelineStage.COMPETENCY_VALIDATION: self.competency_validation,
            PipelineStage.COMPETENCY_EXPLANATION: self.competency_explanation,
        }[stage]


class CompetencyPipeline(BasePipeline):
    PIPELINE_VERSION = COMPETENCY_PIPELINE_VERSION

    def __init__(self, engines: CompetencyPipelineEngines | None = None) -> None:
        self._engines = engines or CompetencyPipelineEngines.default()

    @property
    def model_name(self) -> str:
        from app.core.anthropic_client import get_anthropic_model
        return get_anthropic_model()

    async def execute(
        self,
        ctx: CompetencyPipelineContext,
        *,
        on_stage_complete: StagePersistCallback | None = None,
    ) -> PipelineExecutionResult:
        result = PipelineExecutionResult()
        run_id = str(ctx.pipeline_run_id) if ctx.pipeline_run_id else None
        assessment_id = str(ctx.assessment_id) if ctx.assessment_id else None

        for stage in COMPETENCY_PIPELINE_STAGES:
            stage_input = ctx.build_stage_input(stage)
            completed = ctx.completed_stages()

            if stage in completed:
                existing_output = self._get_stage_output(ctx, stage)
                stage_result = await self._run_stage_skipped(
                    name=stage.value,
                    input_data=stage_input,
                    output_data=existing_output,
                    pipeline_run_id=run_id,
                    assessment_id=assessment_id,
                )
                result.stage_results.append(stage_result)
                continue

            engine_fn = self._engines.get_engine(stage)
            stage_result = await self._run_stage(
                name=stage.value,
                engine_fn=engine_fn,
                input_data=stage_input,
                pipeline_run_id=run_id,
                assessment_id=assessment_id,
                model_name=self.model_name,
                pipeline_version=self.PIPELINE_VERSION,
            )
            result.stage_results.append(stage_result)
            result.total_duration_seconds += stage_result.duration_seconds

            if not stage_result.success:
                result.failed_stage = stage.value
                result.error_message = stage_result.error_message
                return result

            ctx.apply_stage_output(stage, stage_result.output_data)
            if on_stage_complete:
                await on_stage_complete(stage, stage_result.output_data, stage_result.duration_seconds)

        return result

    @staticmethod
    def _get_stage_output(ctx: CompetencyPipelineContext, stage: PipelineStage) -> Any:
        return {
            PipelineStage.ROLE_UNDERSTANDING: ctx.role_understanding,
            PipelineStage.COMPETENCY_DISCOVERY: ctx.competency_discovery,
            PipelineStage.COMPETENCY_STRUCTURING: ctx.competency_structuring,
            PipelineStage.COMPETENCY_VALIDATION: ctx.competency_validation,
            PipelineStage.COMPETENCY_EXPLANATION: ctx.competency_explanation,
        }[stage]

    @staticmethod
    def assemble_final_output(explanation_output: dict[str, Any]) -> dict[str, Any]:
        return {
            "profession_summary": explanation_output.get("profession_summary"),
            "competencies": explanation_output.get("competencies", []),
        }

    @staticmethod
    def build_error_details(stage: str, exc_message: str) -> dict[str, Any]:
        tb = traceback.format_exc()
        return {
            "stage": stage,
            "exception_type": "PipelineStageError",
            "message": exc_message,
            "traceback_hash": hashlib.sha256(tb.encode()).hexdigest()[:16],
        }
