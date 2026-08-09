"""Dispatch long-running jobs to Celery or FastAPI BackgroundTasks."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import BackgroundTasks

from app.core.config import settings

logger = logging.getLogger(__name__)


def dispatch_competency_pipeline(
    background_tasks: BackgroundTasks,
    *,
    assessment_id: UUID,
    run_pipeline,
) -> None:
    """Queue competency pipeline on Celery when enabled, otherwise BackgroundTasks."""
    if settings.USE_CELERY:
        from app.tasks.pipeline import run_competency_pipeline_task

        run_competency_pipeline_task.delay(str(assessment_id))
        logger.info("Dispatched competency pipeline to Celery assessment_id=%s", assessment_id)
        return

    background_tasks.add_task(run_pipeline, assessment_id)
