from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.core.constants import PASSWORD_REGEX

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class OTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class OTPVerificationResponse(BaseModel):
    verification_token: str

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(..., pattern=PASSWORD_REGEX)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., pattern=PASSWORD_REGEX)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    verification_token: str
    new_password: str = Field(..., pattern=PASSWORD_REGEX)

class LogoutRequest(BaseModel):
    refresh_token: str | None = None
