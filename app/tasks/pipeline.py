"""Background pipeline tasks for Celery workers."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.celery_app import celery_app
from app.dependencies.pipeline import get_assessment_service

logger = logging.getLogger(__name__)


@celery_app.task(name="careershift.run_competency_pipeline", bind=True, max_retries=2)
def run_competency_pipeline_task(self, assessment_id: str) -> None:
    """Run competency mapping pipeline in a Celery worker."""
    service = get_assessment_service()
    try:
        asyncio.run(service.run_competency_pipeline(UUID(assessment_id)))
    except Exception as exc:
        logger.exception("Celery competency pipeline failed assessment_id=%s", assessment_id)
        raise self.retry(exc=exc, countdown=30) from exc
