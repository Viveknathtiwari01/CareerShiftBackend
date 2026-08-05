from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_task import AssessmentTask
from app.models.assessment_task_analysis import AssessmentTaskAnalysis


class AssessmentTaskAnalysisRepository:
    async def list_for_assessment(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
        selected_only: bool = True,
    ) -> list[AssessmentTaskAnalysis]:
        query = (
            select(AssessmentTaskAnalysis)
            .join(AssessmentTask, AssessmentTaskAnalysis.task_id == AssessmentTask.id)
            .where(
                AssessmentTask.assessment_id == assessment_id,
                AssessmentTask.is_deleted == False,  # noqa: E712
                AssessmentTaskAnalysis.is_deleted == False,  # noqa: E712
            )
            .options(selectinload(AssessmentTaskAnalysis.task))
            .order_by(AssessmentTask.sort_order, AssessmentTask.created_at)
        )
        if selected_only:
            query = query.where(AssessmentTask.selected == True)  # noqa: E712
        result = await db.execute(query)
        return list(result.scalars().all())

    async def delete_for_assessment(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> None:
        subq = select(AssessmentTask.id).where(AssessmentTask.assessment_id == assessment_id)
        await db.execute(
            delete(AssessmentTaskAnalysis).where(AssessmentTaskAnalysis.task_id.in_(subq))
        )
        await db.flush()

    async def bulk_create(
        self,
        db: AsyncSession,
        *,
        rows: list[AssessmentTaskAnalysis],
    ) -> list[AssessmentTaskAnalysis]:
        for row in rows:
            db.add(row)
        await db.flush()
        for row in rows:
            await db.refresh(row)
        return rows


assessment_task_analysis_repo = AssessmentTaskAnalysisRepository()
