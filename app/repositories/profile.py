from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import UserProfile
from app.schemas.profile import UserProfileCreate, UserProfileUpdate
from app.repositories.base import BaseRepository

class ProfileRepository(BaseRepository[UserProfile, UserProfileCreate, UserProfileUpdate]):
    async def get_by_user_id(self, db: AsyncSession, user_id: UUID) -> Optional[UserProfile]:
        result = await db.execute(
            select(UserProfile).filter(
                UserProfile.user_id == user_id, 
                UserProfile.is_deleted == False
            )
        )
        return result.scalars().first()

profile_repo = ProfileRepository(UserProfile)
