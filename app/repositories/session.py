from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.session import Session
from app.repositories.base import BaseRepository
from uuid import UUID

class SessionRepository(BaseRepository[Session, dict, dict]):
    async def get_by_token_jti(self, db: AsyncSession, *, token_jti: str) -> Optional[Session]:
        result = await db.execute(select(Session).filter(Session.token_jti == token_jti))
        return result.scalars().first()
        
    async def revoke_all_user_sessions(self, db: AsyncSession, *, user_id: UUID) -> None:
        await db.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.is_revoked == False)
            .values(is_revoked=True)
        )
        await db.commit()

session_repo = SessionRepository(Session)
