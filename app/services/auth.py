import uuid
import secrets
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.user import user_repo
from app.repositories.session import session_repo
from app.services.security import SecurityService
from app.services.email import EmailService
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserCreate
from app.core.constants import STATUS_LOCKED
from app.models.otp import OTPCode
from app.core.config import settings
from jose import jwt

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_register_otp(self, req: RegisterRequest) -> None:
        # Check if email/username already exists in the actual user table
        if await user_repo.get_by_email(self.db, email=req.email):
            raise ValueError("Email already registered")
        if await user_repo.get_by_username(self.db, username=req.username):
            raise ValueError("Username already taken")
            
        # Serialize the entire registration payload
        payload_data = req.model_dump_json()
        
        # Generate 6 digit OTP
        otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        code_hash = SecurityService.get_password_hash(otp_code)
        
        # Save to DB inside the OTP table (so we don't pollute users table yet)
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        db_otp = OTPCode(email=req.email, code_hash=code_hash, purpose="registration", payload=payload_data, expires_at=expires)
        self.db.add(db_otp)
        await self.db.commit()
        
        # Send Email
        await EmailService.send_otp_email(to_email=req.email, otp=otp_code, purpose="registration")

    async def verify_register_otp(self, email: str, otp: str) -> dict:
        result = await self.db.execute(
            select(OTPCode)
            .where(OTPCode.email == email, OTPCode.purpose == "registration", OTPCode.is_used == False)
            .order_by(OTPCode.created_at.desc())
        )
        db_otp = result.scalars().first()
        
        if not db_otp:
            raise ValueError("No active verification code found")
        if db_otp.is_expired:
            raise ValueError("Verification code has expired")
        if not SecurityService.verify_password(otp, db_otp.code_hash):
            raise ValueError("Invalid verification code")
            
        db_otp.is_used = True
        
        if not db_otp.payload:
            raise ValueError("Registration data is missing")
            
        req_data = json.loads(db_otp.payload)
        
        # Double check email/username existence again to prevent race conditions
        if await user_repo.get_by_email(self.db, email=req_data["email"]):
            raise ValueError("Email was registered while pending verification")
            
        hashed_pw = SecurityService.get_password_hash(req_data["password"])
        
        create_data = {
            "email": req_data["email"],
            "username": req_data["username"],
            "first_name": req_data.get("first_name"),
            "last_name": req_data.get("last_name"),
            "phone": req_data.get("phone"),
            "password_hash": hashed_pw,
            "email_verified": True
        }
        
        from app.models.user import User
        from app.models.role import Role
        
        # Ensure default User role exists and assign it
        role_result = await self.db.execute(select(Role).where(Role.name == "User"))
        user_role = role_result.scalars().first()
        
        if not user_role:
            user_role = Role(name="User", description="Standard platform user")
            self.db.add(user_role)
            await self.db.commit()
            
        db_user = User(**create_data)
        db_user.roles.append(user_role)
        
        self.db.add(db_user)
        self.db.add(db_otp)
        await self.db.commit()
        await self.db.refresh(db_user)
        
        return {"id": str(db_user.id), "email": db_user.email}

    async def request_password_reset_otp(self, email: str) -> None:
        if not await user_repo.get_by_email(self.db, email=email):
            raise ValueError("User with this email not found")
            
        otp_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        code_hash = SecurityService.get_password_hash(otp_code)
        
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        db_otp = OTPCode(email=email, code_hash=code_hash, purpose="password_reset", expires_at=expires)
        self.db.add(db_otp)
        await self.db.commit()
        
        await EmailService.send_otp_email(to_email=email, otp=otp_code, purpose="password_reset")

    async def verify_password_reset_otp(self, email: str, otp: str) -> str:
        result = await self.db.execute(
            select(OTPCode)
            .where(OTPCode.email == email, OTPCode.purpose == "password_reset", OTPCode.is_used == False)
            .order_by(OTPCode.created_at.desc())
        )
        db_otp = result.scalars().first()
        
        if not db_otp:
            raise ValueError("No active verification code found")
        if db_otp.is_expired:
            raise ValueError("Verification code has expired")
        if not SecurityService.verify_password(otp, db_otp.code_hash):
            raise ValueError("Invalid verification code")
            
        db_otp.is_used = True
        self.db.add(db_otp)
        await self.db.commit()
        
        to_encode = {"sub": email, "type": "verification", "purpose": "password_reset"}
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return encoded_jwt

    async def reset_password(self, verification_token: str, new_password: str) -> None:
        try:
            payload = jwt.decode(verification_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            token_email = payload.get("sub")
            token_type = payload.get("type")
            token_purpose = payload.get("purpose")
            
            if token_type != "verification" or token_purpose != "password_reset" or not token_email:
                raise ValueError("Invalid verification token")
        except Exception:
            raise ValueError("Invalid or expired verification token")
            
        user = await user_repo.get_by_email(self.db, email=token_email)
        if not user:
            raise ValueError("User not found")
            
        user.password_hash = SecurityService.get_password_hash(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        
        self.db.add(user)
        await self.db.commit()

    async def login(self, req: LoginRequest, ip: str, user_agent: str) -> TokenResponse:
        user = await user_repo.get_by_email(self.db, email=req.email)
        if not user:
            raise ValueError("Invalid email or password")
            
        if user.status == STATUS_LOCKED:
            raise ValueError("Account is locked")
            
        if not SecurityService.verify_password(req.password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.status = STATUS_LOCKED
                user.locked_until = datetime.now(timezone.utc)
            self.db.add(user)
            await self.db.commit()
            raise ValueError("Invalid email or password")
            
        user.failed_login_attempts = 0
        user.last_login = datetime.now(timezone.utc)
        self.db.add(user)
        
        access_token = SecurityService.create_access_token(subject=user.id)
        jti = str(uuid.uuid4())
        refresh_token = SecurityService.create_refresh_token(subject=user.id, jti=jti)
        
        from app.models.session import Session
        db_session = Session(
            user_id=user.id,
            token_jti=jti,
            login_time=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            ip_address=ip,
            user_agent=user_agent
        )
        self.db.add(db_session)
        await self.db.commit()
        
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def logout(self, user_id: uuid.UUID, token_jti: str) -> None:
        session = await session_repo.get_by_token_jti(self.db, token_jti=token_jti)
        if session and session.user_id == user_id:
            session.is_revoked = True
            session.logout_time = datetime.now(timezone.utc)
            self.db.add(session)
            await self.db.commit()
