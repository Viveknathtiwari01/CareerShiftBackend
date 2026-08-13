from uuid import UUID

from fastapi import Depends

from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.dependencies.auth import get_current_user
from app.models.user import User


async def rate_limit_assessment_start(current_user: User = Depends(get_current_user)) -> User:
    await enforce_rate_limit(
        f"assessment_start:{current_user.id}",
        limit=settings.ASSESSMENT_START_RATE_LIMIT,
        window_seconds=settings.ASSESSMENT_START_RATE_WINDOW_SECONDS,
        label="assessment starts",
    )
    return current_user


async def rate_limit_report_generate(current_user: User = Depends(get_current_user)) -> User:
    await enforce_rate_limit(
        f"report_generate:{current_user.id}",
        limit=settings.REPORT_GENERATE_RATE_LIMIT,
        window_seconds=settings.REPORT_GENERATE_RATE_WINDOW_SECONDS,
        label="report generation",
    )
    return current_user


async def rate_limit_analyze(current_user: User = Depends(get_current_user)) -> User:
    await enforce_rate_limit(
        f"analyze:{current_user.id}",
        limit=settings.ANALYZE_RATE_LIMIT,
        window_seconds=settings.ANALYZE_RATE_WINDOW_SECONDS,
        label="3B analysis",
    )
    return current_user


async def rate_limit_suggest_identity(current_user: User = Depends(get_current_user)) -> User:
    await enforce_rate_limit(
        f"suggest_identity:{current_user.id}",
        limit=settings.SUGGEST_IDENTITY_RATE_LIMIT,
        window_seconds=settings.SUGGEST_IDENTITY_RATE_WINDOW_SECONDS,
        label="career identity suggestions",
    )
    return current_user
