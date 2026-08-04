import pytest
from uuid import uuid4

from app.pipelines.context import CompetencyPipelineContext
from app.pipelines.stages import PipelineStage
from app.services.competency_pipeline import CompetencyPipeline, CompetencyPipelineEngines
from tests.test_pipeline_context import DISCOVERY_OUTPUT, ROLE_OUTPUT, SAMPLE_PROFILE


def _make_engines(
    *,
    fail_at: PipelineStage | None = None,
) -> CompetencyPipelineEngines:
    def role_run(_):
        return ROLE_OUTPUT

    def discovery_run(_):
        return DISCOVERY_OUTPUT

    def structuring_run(_):
        raise RuntimeError("Structuring failed")

    def validation_run(_):
        return {"validated_competencies": [{"name": "Test"}]}

    def explanation_run(_):
        return {
            "profession_summary": "Summary",
            "competencies": [{"name": "Test", "category": "Technical"}],
        }

    return CompetencyPipelineEngines(
        role_understanding=role_run,
        competency_discovery=discovery_run if fail_at != PipelineStage.COMPETENCY_DISCOVERY else structuring_run,
        competency_structuring=structuring_run if fail_at == PipelineStage.COMPETENCY_STRUCTURING else (lambda _: [{"name": "X", "category": "Technical", "description": "d"}]),
        competency_validation=validation_run,
        competency_explanation=explanation_run,
    )


@pytest.mark.asyncio
async def test_pipeline_runs_all_stages():
    pipeline = CompetencyPipeline(engines=_make_engines())
    ctx = CompetencyPipelineContext(profile=SAMPLE_PROFILE, pipeline_run_id=uuid4())
    persisted: list[tuple[PipelineStage, object, float]] = []

    async def on_complete(stage, output, duration):
        persisted.append((stage, output, duration))

    result = await pipeline.execute(ctx, on_stage_complete=on_complete)

    assert result.success
    assert result.failed_stage is None
    assert len(persisted) == 5
    assert ctx.competency_explanation is not None


@pytest.mark.asyncio
async def test_pipeline_failure_at_structuring():
    pipeline = CompetencyPipeline(engines=_make_engines(fail_at=PipelineStage.COMPETENCY_STRUCTURING))
    ctx = CompetencyPipelineContext(profile=SAMPLE_PROFILE, pipeline_run_id=uuid4())
    persisted: list[PipelineStage] = []

    async def on_complete(stage, output, duration):
        persisted.append(stage)

    result = await pipeline.execute(ctx, on_stage_complete=on_complete)

    assert not result.success
    assert result.failed_stage == PipelineStage.COMPETENCY_STRUCTURING.value
    assert PipelineStage.ROLE_UNDERSTANDING in persisted
    assert PipelineStage.COMPETENCY_DISCOVERY in persisted
    assert PipelineStage.COMPETENCY_STRUCTURING not in persisted


@pytest.mark.asyncio
async def test_pipeline_skips_completed_stages_on_resume():
    pipeline = CompetencyPipeline(engines=_make_engines(fail_at=PipelineStage.COMPETENCY_STRUCTURING))
    ctx = CompetencyPipelineContext(
        profile=SAMPLE_PROFILE,
        role_understanding=ROLE_OUTPUT,
        competency_discovery=DISCOVERY_OUTPUT,
        pipeline_run_id=uuid4(),
    )
    call_count = {"structuring": 0}

    engines = _make_engines(fail_at=PipelineStage.COMPETENCY_STRUCTURING)

    def structuring_run(input_data):
        call_count["structuring"] += 1
        return [{"name": "Resumed", "category": "Technical", "description": "d"}]

    engines.competency_structuring = structuring_run
    pipeline = CompetencyPipeline(engines=engines)

    result = await pipeline.execute(ctx)

    assert result.success
    assert call_count["structuring"] == 1


def test_assemble_final_output():
    explanation = {
        "profession_summary": "HRIS professional",
        "competencies": [{"name": "HRIS Configuration", "category": "Technical"}],
    }
    final = CompetencyPipeline.assemble_final_output(explanation)
    assert final["profession_summary"] == "HRIS professional"
    assert len(final["competencies"]) == 1
