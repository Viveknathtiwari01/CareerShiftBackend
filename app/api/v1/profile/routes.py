from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.profile import UserProfileCreate, UserProfileUpdate, UserProfileResponse, GenerateSkillsRequest
from app.schemas.common import APIResponse
from app.services.profile import profile_service
from app.services.ai_skills import generate_skills_from_ai

router = APIRouter()

@router.get("/me", response_model=APIResponse[UserProfileResponse])
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await profile_service.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        
    return APIResponse(
        success=True,
        message="Profile retrieved successfully",
        data=UserProfileResponse.model_validate(profile)
    )

@router.get("/me/status", response_model=APIResponse[dict])
async def get_profile_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await profile_service.get_profile(db, current_user.id)
    is_completed = profile is not None
    return APIResponse(
        success=True,
        message="Profile status retrieved",
        data={"is_completed": is_completed}
    )

@router.post("/me", response_model=APIResponse[UserProfileResponse], status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    req: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await profile_service.create_profile(db, current_user.id, req)
    return APIResponse(
        success=True,
        message="Profile created successfully",
        data=UserProfileResponse.model_validate(profile)
    )

@router.put("/me", response_model=APIResponse[UserProfileResponse])
async def update_my_profile(
    req: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await profile_service.update_profile(db, current_user.id, req)
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=UserProfileResponse.model_validate(profile)
    )

@router.patch("/me", response_model=APIResponse[UserProfileResponse])
async def patch_my_profile(
    req: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await profile_service.update_profile(db, current_user.id, req)
    return APIResponse(
        success=True,
        message="Profile partially updated successfully",
        data=UserProfileResponse.model_validate(profile)
    )

@router.post("/generate-skills", response_model=APIResponse[dict])
async def generate_skills_api(
    req: GenerateSkillsRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        skills = await generate_skills_from_ai(
            job_title=req.job_title,
            industry=req.industry,
            business_function=req.business_function,
            functional_domain=req.functional_domain,
            specialization=req.specialization,
            experience=req.experience,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    if not any(skills.values()):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned empty skill lists. Please try again.",
        )

    return APIResponse(
        success=True,
        message="Skills generated successfully",
        data=skills,
    )
