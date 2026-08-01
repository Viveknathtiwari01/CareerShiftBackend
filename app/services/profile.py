from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.profile import UserProfile
from app.schemas.profile import UserProfileCreate, UserProfileUpdate
from app.repositories.profile import profile_repo

class ProfileService:
    async def get_profile(self, db: AsyncSession, user_id: UUID) -> Optional[UserProfile]:
        return await profile_repo.get_by_user_id(db, user_id)

    async def create_profile(self, db: AsyncSession, user_id: UUID, obj_in: UserProfileCreate) -> UserProfile:
        existing_profile = await profile_repo.get_by_user_id(db, user_id)
        if existing_profile:
            raise HTTPException(status_code=400, detail="Profile already exists for this user.")
        
        # We need to pass the user_id when creating the profile
        obj_in_data = obj_in.model_dump()
        obj_in_data["user_id"] = user_id
        
        # We can't directly use profile_repo.create with obj_in because obj_in doesn't have user_id, 
        # so we'll construct the dict directly or use a private schema.
        # But actually obj_in doesn't have user_id, so we modify the creation step.
        db_obj = UserProfile(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_profile(self, db: AsyncSession, user_id: UUID, obj_in: UserProfileUpdate) -> UserProfile:
        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found.")
        
        return await profile_repo.update(db, db_obj=profile, obj_in=obj_in)

profile_service = ProfileService()
