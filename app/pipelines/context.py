from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.pipelines.stages import PipelineStage


class CompetencyPipelineContext(BaseModel):
    """Strongly typed carrier for competency pipeline intermediate outputs."""

    profile: dict[str, Any]
    role_understanding: dict[str, Any] | None = None
    competency_discovery: dict[str, Any] | None = None
    competency_structuring: list[dict[str, Any]] | None = None
    competency_validation: dict[str, Any] | None = None
    competency_explanation: dict[str, Any] | None = None

    assessment_id: UUID | None = None
    pipeline_run_id: UUID | None = None
    model_name: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    def build_stage_input(self, stage: PipelineStage) -> dict[str, Any]:
        if stage == PipelineStage.ROLE_UNDERSTANDING:
            return dict(self.profile)

        if stage == PipelineStage.COMPETENCY_DISCOVERY:
            if not self.role_understanding:
                raise ValueError("role_understanding is required for competency_discovery")
            return {
                "profession": self.role_understanding.get("profession"),
                "functional_areas": self.role_understanding.get("functional_areas"),
            }

        if stage == PipelineStage.COMPETENCY_STRUCTURING:
            if not self.role_understanding or not self.competency_discovery:
                raise ValueError("role_understanding and competency_discovery required for structuring")
            return {
                "profession": self.role_understanding.get("profession"),
                "role_family": self.role_understanding.get("role_family"),
                "purpose": self.role_understanding.get("purpose"),
                "competencies": self.competency_discovery,
            }

        if stage == PipelineStage.COMPETENCY_VALIDATION:
            if not self.role_understanding or self.competency_structuring is None:
                raise ValueError("role_understanding and competency_structuring required for validation")
            return {
                "profession": self.role_understanding.get("profession"),
                "purpose": self.role_understanding.get("purpose"),
                "functional_areas": self.role_understanding.get("functional_areas"),
                "competencies": self.competency_structuring,
            }

        if stage == PipelineStage.COMPETENCY_EXPLANATION:
            if not self.role_understanding or not self.competency_validation:
                raise ValueError("role_understanding and competency_validation required for explanation")
            return {
                "profession": self.role_understanding.get("profession"),
                "purpose": self.role_understanding.get("purpose"),
                "validated_competencies": self.competency_validation.get("validated_competencies", []),
            }

        raise ValueError(f"Unknown stage: {stage}")

    def apply_stage_output(self, stage: PipelineStage, output: Any) -> None:
        if stage == PipelineStage.ROLE_UNDERSTANDING:
            self.role_understanding = output
        elif stage == PipelineStage.COMPETENCY_DISCOVERY:
            self.competency_discovery = output
        elif stage == PipelineStage.COMPETENCY_STRUCTURING:
            self.competency_structuring = output
        elif stage == PipelineStage.COMPETENCY_VALIDATION:
            self.competency_validation = output
        elif stage == PipelineStage.COMPETENCY_EXPLANATION:
            self.competency_explanation = output
        else:
            raise ValueError(f"Unknown stage: {stage}")

    def completed_stages(self) -> set[PipelineStage]:
        completed: set[PipelineStage] = set()
        if self.role_understanding is not None:
            completed.add(PipelineStage.ROLE_UNDERSTANDING)
        if self.competency_discovery is not None:
            completed.add(PipelineStage.COMPETENCY_DISCOVERY)
        if self.competency_structuring is not None:
            completed.add(PipelineStage.COMPETENCY_STRUCTURING)
        if self.competency_validation is not None:
            completed.add(PipelineStage.COMPETENCY_VALIDATION)
        if self.competency_explanation is not None:
            completed.add(PipelineStage.COMPETENCY_EXPLANATION)
        return completed
