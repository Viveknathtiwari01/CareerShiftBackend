"""Celery application — enable with USE_CELERY=true and run: celery -A app.celery_app worker -l info"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "careershift",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/0",
    include=["app.tasks.pipeline"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
