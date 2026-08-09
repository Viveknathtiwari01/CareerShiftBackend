import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PIPELINE_STATUS_COMPLETED
from app.models.assessment_task_analysis import AssessmentTaskAnalysis
from app.repositories.assessment import assessment_repo
from app.repositories.assessment_task import assessment_task_repo
from app.repositories.assessment_task_analysis import (
    AssessmentTaskAnalysisRepository,
    assessment_task_analysis_repo,
)
from app.repositories.competency_mapping import competency_mapping_repo
from app.repositories.profile import profile_repo
from app.schemas.assessment_task_analysis import TaskAnalysisItem, TaskAnalysisRunResponse
from app.services.profile_mapper import profile_to_pipeline_input
from app.services.report_generator import analysis_dicts_from_rows, build_toolkit_from_analyses
from app.services.task_3b_classification import classify_tasks_3b_from_ai

logger = logging.getLogger(__name__)


class AssessmentTaskAnalysisService:
    def __init__(
        self,
        repository: AssessmentTaskAnalysisRepository | None = None,
    ) -> None:
        self._repo = repository or assessment_task_analysis_repo

    async def _get_owned_assessment(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ):
        assessment = await assessment_repo.get_by_id_for_user(
            db, assessment_id=assessment_id, user_id=user_id
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")
        return assessment

    def _to_item(self, row: AssessmentTaskAnalysis) -> TaskAnalysisItem:
        task = row.task
        return TaskAnalysisItem(
            task_id=row.task_id,
            task_title=task.title if task else "",
            task_description=task.description if task else None,
            task_category=task.category if task else None,
            category=row.category,
            rationale=row.rationale,
            reason=row.reason,
            next_actions=list(row.next_actions or [])[:3],
            auto_potential=row.auto_potential,
            risk_level=row.risk_level,
            future_impact=row.future_impact,
            recommended_tools=list(row.recommended_tools or []),
        )

    @staticmethod
    def _task_title_for_row(row: AssessmentTaskAnalysis) -> str:
        return row.task.title if row.task else ""

    async def _persist_toolkit_snapshot(
        self,
        db: AsyncSession,
        assessment,
        analyses: list[dict],
    ) -> None:
        assessment.ai_toolkit_json = {"tools": build_toolkit_from_analyses(analyses)}
        db.add(assessment)
        await db.flush()

    async def get_analysis(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> TaskAnalysisRunResponse:
        await self._get_owned_assessment(db, user_id, assessment_id)
        rows = await self._repo.list_for_assessment(db, assessment_id=assessment_id)
        return TaskAnalysisRunResponse(
            analyses=[self._to_item(r) for r in rows],
            regenerated=False,
        )

    async def analyze_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        *,
        regenerate: bool = False,
    ) -> TaskAnalysisRunResponse:
        assessment = await self._get_owned_assessment(db, user_id, assessment_id)

        if assessment.status != PIPELINE_STATUS_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competency mapping must complete before 3B analysis.",
            )

        all_tasks = await assessment_task_repo.list_for_assessment(db, assessment_id=assessment_id)
        selected_tasks = [t for t in all_tasks if t.selected]
        if len(selected_tasks) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one selected task is required for 3B analysis.",
            )

        existing = await self._repo.list_for_assessment(db, assessment_id=assessment_id)
        existing_task_ids = {r.task_id for r in existing}
        selected_ids = {t.id for t in selected_tasks}

        if (
            existing
            and not regenerate
            and existing_task_ids == selected_ids
            and len(existing) == len(selected_tasks)
        ):
            if not (assessment.ai_toolkit_json or {}).get("tools"):
                analyses_payload = analysis_dicts_from_rows(
                    existing,
                    task_title_for=self._task_title_for_row,
                )
                await self._persist_toolkit_snapshot(db, assessment, analyses_payload)
                await db.commit()
            summary = self._average_confidence(existing)
            return TaskAnalysisRunResponse(
                analyses=[self._to_item(r) for r in existing],
                summary_confidence=summary,
                regenerated=False,
            )

        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        mapping = await competency_mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
        profession_summary = None
        if mapping and mapping.final_output_json:
            profession_summary = mapping.final_output_json.get("profession_summary")

        profile_data = profile_to_pipeline_input(profile)
        profile_data.update(
            {
                "salary": profile.salary,
                "professional_skills": profile.professional_skills or [],
                "soft_skills": profile.soft_skills or [],
                "behavioural_skills": profile.behavioural_skills or [],
                "digital_skills": profile.digital_skills or [],
                "ai_frequency": profile.ai_frequency,
                "ai_tools": profile.ai_tools or [],
                "ai_comfort_level": profile.ai_comfort_level,
            }
        )

        task_payloads = [
            {
                "title": t.title,
                "description": t.description,
                "category": t.category,
                "hours_per_week": t.hours_per_week,
                "time_allocation": t.time_allocation if t.time_allocation is not None else t.hours_per_week,
                "complexity": t.complexity,
                "creativity": t.creativity,
                "human_touch": t.human_touch,
                "frequency": t.frequency,
                "business_criticality": t.business_criticality,
                "ai_assistance": t.ai_assistance,
                "confidence_score": t.confidence_score if t.confidence_score is not None else 5,
                "manual_notes": t.manual_notes,
            }
            for t in selected_tasks
        ]

        ai_result = await classify_tasks_3b_from_ai(
            profile_data=profile_data,
            profession_summary=profession_summary,
            tasks=task_payloads,
        )

        analyses_by_index = {item["task_index"]: item for item in ai_result.get("analyses", [])}

        await self._repo.delete_for_assessment(db, assessment_id=assessment_id)

        new_rows: list[AssessmentTaskAnalysis] = []
        for idx, task in enumerate(selected_tasks):
            item = analyses_by_index.get(idx)
            if not item:
                logger.error("Missing 3B analysis for task index %d (task_id=%s)", idx, task.id)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "AI analysis did not return results for all tasks. "
                        "Please retry the analysis."
                    ),
                )

            new_rows.append(
                AssessmentTaskAnalysis(
                    task_id=task.id,
                    category=item["category"],
                    rationale=item.get("rationale"),
                    reason=item.get("reason"),
                    next_actions=item.get("next_actions") or [],
                    auto_potential=item.get("auto_potential"),
                    risk_level=item.get("risk_level"),
                    future_impact=item.get("future_impact"),
                    recommended_tools=item.get("recommended_tools") or [],
                )
            )

        created = await self._repo.bulk_create(db, rows=new_rows)
        analyses_payload = [
            {
                "task_id": str(row.task_id),
                "task_title": task.title,
                "category": row.category,
                "rationale": row.rationale,
                "reason": row.reason,
                "future_impact": row.future_impact,
                "auto_potential": row.auto_potential,
                "risk_level": row.risk_level,
                "recommended_tools": list(row.recommended_tools or []),
            }
            for row, task in zip(created, selected_tasks)
        ]
        await self._persist_toolkit_snapshot(db, assessment, analyses_payload)
        await db.commit()

        logger.info("3B analysis saved for assessment %s (%d tasks)", assessment_id, len(created))

        return TaskAnalysisRunResponse(
            analyses=[self._to_item(r) for r in created],
            summary_confidence=ai_result.get("summary_confidence"),
            regenerated=regenerate or bool(existing),
        )

    @staticmethod
    def _average_confidence(rows: list[AssessmentTaskAnalysis]) -> int | None:
        potentials = [r.auto_potential for r in rows if r.auto_potential is not None]
        if not potentials:
            return None
        return round(sum(potentials) / len(potentials))


assessment_task_analysis_service = AssessmentTaskAnalysisService()
