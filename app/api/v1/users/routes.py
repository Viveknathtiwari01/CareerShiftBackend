from fastapi import APIRouter, Depends
from app.schemas.user import UserResponse
from app.schemas.common import APIResponse
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    return APIResponse(
        success=True,
        message="User profile retrieved successfully",
        data=UserResponse.model_validate(current_user)
    )

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.user import UserUpdate, PasswordChangeRequest
from app.services.security import SecurityService
from app.repositories.user import user_repo

@router.put("/me", response_model=APIResponse[UserResponse])
async def update_me(
    req: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    update_data = req.model_dump(exclude_unset=True)
    updated_user = await user_repo.update(db, db_obj=current_user, obj_in=update_data)
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=UserResponse.model_validate(updated_user)
    )

@router.put("/me/password", response_model=APIResponse[None])
async def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New passwords do not match")
        
    if not SecurityService.verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password")
        
    from datetime import datetime, timezone
    current_user.password_hash = SecurityService.get_password_hash(req.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    
    db.add(current_user)
    await db.commit()
    
    return APIResponse(
        success=True,
        message="Password changed successfully"
    )
