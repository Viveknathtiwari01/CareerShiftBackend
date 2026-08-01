from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate
from pydantic import EmailStr

class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: EmailStr) -> Optional[User]:
        result = await db.execute(select(User).filter(User.email == email, User.is_deleted == False))
        return result.scalars().first()
        
    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        result = await db.execute(select(User).filter(User.username == username, User.is_deleted == False))
        return result.scalars().first()

user_repo = UserRepository(User)
