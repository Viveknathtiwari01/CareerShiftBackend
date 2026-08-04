import asyncio
import logging
import time
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Callable

from app.pipelines.engine_protocol import EngineRunFn

logger = logging.getLogger(__name__)


@dataclass
class PipelineStageResult:
    name: str
    input_data: dict[str, Any]
    output_data: Any | None = None
    duration_seconds: float = 0.0
    success: bool = False
    error_message: str | None = None
    skipped: bool = False


@dataclass
class PipelineExecutionResult:
    stage_results: list[PipelineStageResult] = field(default_factory=list)
    failed_stage: str | None = None
    error_message: str | None = None
    total_duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.failed_stage is None


class BasePipeline(ABC):
    """Shared pipeline infrastructure for stage execution and logging."""

    async def _run_stage(
        self,
        *,
        name: str,
        engine_fn: EngineRunFn,
        input_data: dict[str, Any],
        pipeline_run_id: str | None = None,
        assessment_id: str | None = None,
        model_name: str | None = None,
        pipeline_version: str | None = None,
    ) -> PipelineStageResult:
        log_extra = {
            "pipeline_run_id": pipeline_run_id,
            "assessment_id": assessment_id,
            "stage": name,
            "model_name": model_name,
            "pipeline_version": pipeline_version,
        }
        logger.info("Starting %s", name, extra=log_extra)
        start = time.perf_counter()
        try:
            output = await asyncio.to_thread(engine_fn, input_data)
            duration = time.perf_counter() - start
            logger.info(
                "Completed %s in %.2fs",
                name,
                duration,
                extra={**log_extra, "duration_seconds": duration},
            )
            return PipelineStageResult(
                name=name,
                input_data=input_data,
                output_data=output,
                duration_seconds=duration,
                success=True,
            )
        except Exception as exc:
            duration = time.perf_counter() - start
            logger.exception(
                "Failed %s after %.2fs: %s",
                name,
                duration,
                exc,
                extra={**log_extra, "duration_seconds": duration},
            )
            return PipelineStageResult(
                name=name,
                input_data=input_data,
                duration_seconds=duration,
                success=False,
                error_message=str(exc),
            )

    async def _run_stage_skipped(
        self,
        *,
        name: str,
        input_data: dict[str, Any],
        output_data: Any,
        pipeline_run_id: str | None = None,
        assessment_id: str | None = None,
    ) -> PipelineStageResult:
        logger.info(
            "Skipping %s — already completed",
            name,
            extra={
                "pipeline_run_id": pipeline_run_id,
                "assessment_id": assessment_id,
                "stage": name,
            },
        )
        return PipelineStageResult(
            name=name,
            input_data=input_data,
            output_data=output_data,
            duration_seconds=0.0,
            success=True,
            skipped=True,
        )


StagePersistCallback = Callable[..., Any]
