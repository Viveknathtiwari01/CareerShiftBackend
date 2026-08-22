from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TASK_SOURCE_AI
from app.models.assessment_task import AssessmentTask
from app.repositories.assessment_task_analysis import assessment_task_analysis_repo
from app.repositories.career_intelligence_report import career_intelligence_report_repo
from app.services.task_content_hash import compute_tasks_content_hash


class AssessmentTaskRepository:
    async def list_for_assessment(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> list[AssessmentTask]:
        result = await db.execute(
            select(AssessmentTask)
            .where(
                AssessmentTask.assessment_id == assessment_id,
                AssessmentTask.is_deleted == False,  # noqa: E712
            )
            .order_by(AssessmentTask.sort_order, AssessmentTask.created_at)
        )
        return list(result.scalars().all())

    async def count_for_assessment(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> int:
        tasks = await self.list_for_assessment(db, assessment_id=assessment_id)
        return len(tasks)

    async def delete_ai_generated(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> None:
        await db.execute(
            delete(AssessmentTask).where(
                AssessmentTask.assessment_id == assessment_id,
                AssessmentTask.source == TASK_SOURCE_AI,
            )
        )
        await db.flush()

    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        tasks: list[AssessmentTask],
    ) -> list[AssessmentTask]:
        for task in tasks:
            db.add(task)
        await db.flush()
        for task in tasks:
            await db.refresh(task)
        return tasks

    async def replace_all_for_assessment(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
        tasks: list[AssessmentTask],
        force_invalidate_analysis: bool = False,
    ) -> list[AssessmentTask]:
        existing = await self.list_for_assessment(db, assessment_id=assessment_id)
        incoming_hash = compute_tasks_content_hash(tasks)
        existing_hash = compute_tasks_content_hash(existing)
        tasks_changed = incoming_hash != existing_hash or len(existing) != len(tasks)

        if tasks_changed or force_invalidate_analysis:
            await assessment_task_analysis_repo.delete_for_assessment(
                db, assessment_id=assessment_id
            )
            await career_intelligence_report_repo.delete_for_assessment(
                db, assessment_id=assessment_id
            )
            await db.execute(
                delete(AssessmentTask).where(AssessmentTask.assessment_id == assessment_id)
            )
            await db.flush()
            return await self.bulk_create(db, tasks=tasks)

        return existing


assessment_task_repo = AssessmentTaskRepository()
