import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PIPELINE_STATUS_COMPLETED, TASK_SOURCE_AI, TASK_SOURCE_USER
from app.models.assessment_task import AssessmentTask
from app.repositories.assessment import assessment_repo
from app.repositories.assessment_task import AssessmentTaskRepository, assessment_task_repo
from app.repositories.competency_mapping import competency_mapping_repo
from app.repositories.profile import profile_repo
from app.schemas.assessment_task import (
    AssessmentTaskResponse,
    AssessmentTaskUpsertItem,
    AssessmentTasksBulkUpsert,
    SuggestedTaskItem,
    TaskGenerationResponse,
)
from app.services.profile_mapper import profile_to_pipeline_input
from app.services.task_generation import generate_tasks_from_ai

logger = logging.getLogger(__name__)


class AssessmentTaskService:
    def __init__(self, repository: AssessmentTaskRepository | None = None) -> None:
        self._repo = repository or assessment_task_repo

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

    async def get_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> list[AssessmentTaskResponse]:
        await self._get_owned_assessment(db, user_id, assessment_id)
        tasks = await self._repo.list_for_assessment(db, assessment_id=assessment_id)
        return [AssessmentTaskResponse.model_validate(t) for t in tasks]

    async def generate_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        *,
        regenerate: bool = False,
    ) -> TaskGenerationResponse:
        assessment = await self._get_owned_assessment(db, user_id, assessment_id)

        if assessment.status != PIPELINE_STATUS_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competency mapping must complete before generating tasks.",
            )

        existing = await self._repo.list_for_assessment(db, assessment_id=assessment_id)
        if existing and not regenerate:
            return TaskGenerationResponse(
                tasks=[AssessmentTaskResponse.model_validate(t) for t in existing],
                suggested_additional=[],
                regenerated=False,
            )

        mapping = await competency_mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
        if not mapping or not mapping.final_output_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competency mapping output not available.",
            )

        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        profile_data = profile_to_pipeline_input(profile)
        profile_data["industry"] = profile.industry
        profile_data["business_function"] = profile.business_function
        profile_data["domain"] = profile.domain
        profile_data["specialization"] = profile.specialization

        final_output = mapping.final_output_json
        competencies = final_output.get("competencies", [])

        ai_result = await generate_tasks_from_ai(
            profile_data=profile_data,
            competencies=competencies,
            profession_summary=final_output.get("profession_summary"),
        )

        primary_tasks = ai_result.get("tasks", [])
        if len(primary_tasks) < 3:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI generated insufficient tasks. Please retry.",
            )

        if regenerate:
            user_snapshots = [
                {
                    "title": t.title,
                    "description": t.description,
                    "category": t.category,
                    "hours_per_week": t.hours_per_week,
                    "complexity": t.complexity,
                    "creativity": t.creativity,
                    "human_touch": t.human_touch,
                    "confidence": t.confidence,
                    "selected": t.selected,
                    "frequency": t.frequency,
                    "business_criticality": t.business_criticality,
                    "time_allocation": t.time_allocation,
                    "ai_assistance": t.ai_assistance,
                    "confidence_score": t.confidence_score,
                    "manual_notes": t.manual_notes,
                }
                for t in existing
                if t.source == TASK_SOURCE_USER
            ]
            await self._repo.replace_all_for_assessment(db, assessment_id=assessment_id, tasks=[])
        else:
            user_snapshots = []

        new_rows: list[AssessmentTask] = []
        sort_order = 0

        for item in primary_tasks:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            new_rows.append(
                AssessmentTask(
                    assessment_id=assessment_id,
                    title=title,
                    description=item.get("description"),
                    category=item.get("category"),
                    hours_per_week=float(item.get("hours_per_week") or 0),
                    complexity=item.get("complexity") or "medium",
                    creativity=item.get("creativity") or "medium",
                    human_touch=item.get("human_touch") or "medium",
                    confidence=item.get("confidence"),
                    selected=True,
                    source=TASK_SOURCE_AI,
                    sort_order=sort_order,
                )
            )
            sort_order += 1

        for snapshot in user_snapshots:
            new_rows.append(
                AssessmentTask(
                    assessment_id=assessment_id,
                    title=snapshot["title"],
                    description=snapshot["description"],
                    category=snapshot["category"],
                    hours_per_week=snapshot["hours_per_week"],
                    complexity=snapshot["complexity"],
                    creativity=snapshot["creativity"],
                    human_touch=snapshot["human_touch"],
                    confidence=snapshot["confidence"],
                    selected=snapshot["selected"],
                    source=TASK_SOURCE_USER,
                    sort_order=sort_order,
                    frequency=snapshot["frequency"],
                    business_criticality=snapshot["business_criticality"],
                    time_allocation=snapshot["time_allocation"],
                    ai_assistance=snapshot["ai_assistance"],
                    confidence_score=snapshot["confidence_score"],
                    manual_notes=snapshot["manual_notes"],
                )
            )
            sort_order += 1

        if new_rows:
            created = await self._repo.bulk_create(db, tasks=new_rows)
        else:
            created = []
        await db.commit()

        suggested = [
            SuggestedTaskItem.model_validate(item)
            for item in ai_result.get("suggested_additional", [])
            if (item.get("title") or "").strip()
        ]

        logger.info(
            "Generated %d tasks for assessment %s",
            len(created),
            assessment_id,
        )

        return TaskGenerationResponse(
            tasks=[AssessmentTaskResponse.model_validate(t) for t in created],
            suggested_additional=suggested,
            regenerated=regenerate or bool(existing),
        )

    async def save_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        payload: AssessmentTasksBulkUpsert,
    ) -> list[AssessmentTaskResponse]:
        await self._get_owned_assessment(db, user_id, assessment_id)

        selected_count = sum(1 for t in payload.tasks if t.selected)
        if selected_count < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one task must be selected.",
            )

        existing_tasks = await self._repo.list_for_assessment(db, assessment_id=assessment_id)
        existing_ids = {t.id for t in existing_tasks}

        rows: list[AssessmentTask] = []
        for index, item in enumerate(payload.tasks):
            task_id = item.id if item.id in existing_ids else uuid4()
            rows.append(
                AssessmentTask(
                    id=task_id,
                    assessment_id=assessment_id,
                    title=item.title.strip(),
                    description=item.description,
                    category=item.category,
                    hours_per_week=item.hours_per_week,
                    complexity=item.complexity,
                    creativity=item.creativity,
                    human_touch=item.human_touch,
                    confidence=item.confidence,
                    selected=item.selected,
                    source=item.source if item.source in {TASK_SOURCE_AI, TASK_SOURCE_USER} else TASK_SOURCE_USER,
                    sort_order=item.sort_order if item.sort_order else index,
                    frequency=item.frequency,
                    business_criticality=item.business_criticality,
                    time_allocation=item.time_allocation,
                    ai_assistance=item.ai_assistance,
                    confidence_score=item.confidence_score,
                    manual_notes=item.manual_notes,
                )
            )

        saved = await self._repo.replace_all_for_assessment(
            db, assessment_id=assessment_id, tasks=rows
        )
        await db.commit()
        return [AssessmentTaskResponse.model_validate(t) for t in saved]


assessment_task_service = AssessmentTaskService()
