import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PIPELINE_STATUS_COMPLETED
from app.repositories.assessment import assessment_repo
from app.repositories.assessment_task import assessment_task_repo
from app.repositories.assessment_task_analysis import assessment_task_analysis_repo
from app.repositories.competency_mapping import competency_mapping_repo
from app.repositories.profile import profile_repo
from app.schemas.ai_readiness import AIReadinessResponse
from app.services.ai_readiness_scorer import ScorerInput, compute_ai_readiness

logger = logging.getLogger(__name__)


class AIReadinessService:
    async def get_readiness(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> AIReadinessResponse:
        assessment = await assessment_repo.get_by_id_for_user(
            db, assessment_id=assessment_id, user_id=user_id
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        if assessment.status != PIPELINE_STATUS_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competency mapping must complete before AI readiness can be calculated.",
            )

        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        tasks = await assessment_task_repo.list_for_assessment(db, assessment_id=assessment_id)
        selected_tasks = [t for t in tasks if t.selected]
        if not selected_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one selected task is required for AI readiness scoring.",
            )

        analysis_rows = await assessment_task_analysis_repo.list_for_assessment(
            db, assessment_id=assessment_id
        )
        mapping = await competency_mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
        competencies: list[dict] = []
        if mapping and mapping.final_output_json:
            competencies = mapping.final_output_json.get("competencies", [])

        scorer_input = ScorerInput(
            ai_frequency=profile.ai_frequency,
            ai_tools=list(profile.ai_tools or []),
            ai_comfort_level=profile.ai_comfort_level,
            digital_skills_count=len(profile.digital_skills or []),
            tasks=[
                {
                    "ai_assistance": t.ai_assistance,
                    "confidence_score": t.confidence_score,
                }
                for t in selected_tasks
            ],
            analyses=[
                {
                    "category": row.category,
                    "auto_potential": row.auto_potential,
                    "recommended_tools": list(row.recommended_tools or []),
                    "next_actions": list(row.next_actions or []),
                }
                for row in analysis_rows
            ],
            competencies=competencies,
        )

        result = compute_ai_readiness(scorer_input)
        logger.info(
            "AI readiness computed for assessment %s — score=%s tier=%s",
            assessment_id,
            result.overall_score,
            result.tier,
        )
        return result


ai_readiness_service = AIReadinessService()
