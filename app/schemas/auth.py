from pydantic import BaseModel, EmailStr, Field, model_validator
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
    terms_accepted: bool = Field(..., description="User accepted Terms & Conditions")
    privacy_accepted: bool = Field(..., description="User accepted Privacy Policy")

    @model_validator(mode="after")
    def require_legal_consent(self):
        if not self.terms_accepted or not self.privacy_accepted:
            raise ValueError(
                "You must accept the Terms & Conditions and Privacy Policy to create an account."
            )
        return self

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

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
