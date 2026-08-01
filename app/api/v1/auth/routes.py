from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse, 
    OTPRequest, VerifyOTPRequest, OTPVerificationResponse, ResetPasswordRequest
)
from app.schemas.common import APIResponse
from app.services.auth import AuthService
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/register/request-otp", response_model=APIResponse[None])
async def request_register_otp(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.request_register_otp(req)
        return APIResponse(success=True, message="OTP sent to email successfully. Please verify to complete registration.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/register/verify-otp", response_model=APIResponse[dict])
async def verify_register_otp(req: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        result = await auth_service.verify_register_otp(email=req.email, otp=req.otp)
        return APIResponse(success=True, message="Registration completed successfully", data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/password/forgot", response_model=APIResponse[None])
async def forgot_password_otp(req: OTPRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.request_password_reset_otp(email=req.email)
        return APIResponse(success=True, message="Password reset OTP sent to email")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/password/verify-otp", response_model=APIResponse[OTPVerificationResponse])
async def verify_password_otp(req: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        token = await auth_service.verify_password_reset_otp(email=req.email, otp=req.otp)
        return APIResponse(success=True, message="OTP verified", data=OTPVerificationResponse(verification_token=token))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/password/reset", response_model=APIResponse[None])
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        await auth_service.reset_password(verification_token=req.verification_token, new_password=req.new_password)
        return APIResponse(success=True, message="Password reset successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    try:
        tokens = await auth_service.login(req, ip=ip, user_agent=user_agent)
        return APIResponse(success=True, message="Login successful", data=tokens)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.post("/logout", response_model=APIResponse[None])
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return APIResponse(success=True, message="Logged out successfully")
