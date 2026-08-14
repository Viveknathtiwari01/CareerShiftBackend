from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_intelligence_report import CareerIntelligenceReport


class CareerIntelligenceReportRepository:
    async def get_by_assessment_id(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> CareerIntelligenceReport | None:
        result = await db.execute(
            select(CareerIntelligenceReport).where(
                CareerIntelligenceReport.assessment_id == assessment_id,
                CareerIntelligenceReport.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().first()

    async def delete_for_assessment(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> None:
        """Hard-delete report so the next generate rebuilds from current tasks."""
        await db.execute(
            delete(CareerIntelligenceReport).where(
                CareerIntelligenceReport.assessment_id == assessment_id
            )
        )
        await db.flush()

    async def upsert(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
        payload: dict,
    ) -> CareerIntelligenceReport:
        existing = await self.get_by_assessment_id(db, assessment_id=assessment_id)
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
            return existing

        row = CareerIntelligenceReport(assessment_id=assessment_id, **payload)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


career_intelligence_report_repo = CareerIntelligenceReportRepository()
