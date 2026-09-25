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
        
        obj_in_data = obj_in.model_dump()
        obj_in_data["user_id"] = user_id

        db_obj = UserProfile(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_profile(self, db: AsyncSession, user_id: UUID, obj_in: UserProfileUpdate) -> UserProfile:
        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found.")
        
        career_identity_fields = ["job_title", "industry", "business_function", "domain", "specialization"]
        update_data = obj_in.model_dump(exclude_unset=True)
        
        if any(field in update_data for field in career_identity_fields):
            raise HTTPException(status_code=400, detail="You cannot edit your Current Career Identity once it has been created.")
            
        if not update_data:
            return profile
            
        if getattr(profile, "edit_count", 0) >= 3:
            raise HTTPException(status_code=400, detail="You have reached the maximum limit of 3 edits for your profile sections.")
            
        update_data["edit_count"] = getattr(profile, "edit_count", 0) + 1
        
        return await profile_repo.update(db, db_obj=profile, obj_in=update_data)

profile_service = ProfileService()
