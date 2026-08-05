"""Central prompt version registry.

Bump versions here when Backend/promppts/* content changes.
Prompt files themselves are not modified.
"""

from app.pipelines.stages import PipelineStage

PROMPT_VERSIONS: dict[str, str] = {
    PipelineStage.ROLE_UNDERSTANDING.value: "1.0.0",
    PipelineStage.COMPETENCY_DISCOVERY.value: "1.0.0",
    PipelineStage.COMPETENCY_STRUCTURING.value: "1.0.0",
    PipelineStage.COMPETENCY_VALIDATION.value: "1.0.0",
    PipelineStage.COMPETENCY_EXPLANATION.value: "1.0.0",
}


def get_prompt_versions() -> dict[str, str]:
    return dict(PROMPT_VERSIONS)
