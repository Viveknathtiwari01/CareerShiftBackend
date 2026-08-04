import hashlib
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    PIPELINE_STATUS_PENDING,
    PIPELINE_STATUS_PROCESSING,
    PIPELINE_TYPE_COMPETENCY_MAPPING,
)
from app.models.assessment import Assessment


class AssessmentRepository:
    async def acquire_user_lock(self, db: AsyncSession, user_id: UUID) -> None:
        """PostgreSQL advisory transaction lock keyed by user_id."""
        lock_key = int(hashlib.md5(str(user_id).encode()).hexdigest()[:15], 16)
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})

    async def get_active_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        pipeline_type: str = PIPELINE_TYPE_COMPETENCY_MAPPING,
    ) -> Optional[Assessment]:
        result = await db.execute(
            select(Assessment).where(
                Assessment.user_id == user_id,
                Assessment.pipeline_type == pipeline_type,
                Assessment.status.in_([PIPELINE_STATUS_PENDING, PIPELINE_STATUS_PROCESSING]),
                Assessment.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().first()

    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        profile_id: UUID,
        pipeline_type: str = PIPELINE_TYPE_COMPETENCY_MAPPING,
        status: str = PIPELINE_STATUS_PENDING,
    ) -> Assessment:
        assessment = Assessment(
            user_id=user_id,
            profile_id=profile_id,
            pipeline_type=pipeline_type,
            status=status,
        )
        db.add(assessment)
        await db.flush()
        await db.refresh(assessment)
        return assessment

    async def update_status(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
        status: str,
    ) -> None:
        result = await db.execute(select(Assessment).where(Assessment.id == assessment_id))
        assessment = result.scalars().first()
        if assessment:
            assessment.status = status
            db.add(assessment)
            await db.flush()

    async def get_by_id_for_user(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
        user_id: UUID,
    ) -> Optional[Assessment]:
        result = await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.user_id == user_id,
                Assessment.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().first()

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        assessment_id: UUID,
    ) -> Optional[Assessment]:
        result = await db.execute(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().first()


assessment_repo = AssessmentRepository()
