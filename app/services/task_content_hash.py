"""Fingerprint assessment tasks for 3B invalidation decisions."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.assessment_task import AssessmentTask


def _task_signature(task: AssessmentTask | dict[str, Any]) -> dict[str, Any]:
    if isinstance(task, AssessmentTask):
        return {
            "title": (task.title or "").strip(),
            "description": task.description,
            "category": task.category,
            "hours_per_week": task.hours_per_week,
            "complexity": task.complexity,
            "creativity": task.creativity,
            "human_touch": task.human_touch,
            "frequency": task.frequency,
            "business_criticality": task.business_criticality,
            "time_allocation": task.time_allocation,
            "ai_assistance": task.ai_assistance,
            "confidence_score": task.confidence_score,
            "manual_notes": (task.manual_notes or "").strip() if task.manual_notes else None,
            "selected": task.selected,
            "sort_order": task.sort_order,
            "source": task.source,
        }
    return {
        "title": str(task.get("title", "")).strip(),
        "description": task.get("description"),
        "category": task.get("category"),
        "hours_per_week": task.get("hours_per_week"),
        "complexity": task.get("complexity"),
        "creativity": task.get("creativity"),
        "human_touch": task.get("human_touch"),
        "frequency": task.get("frequency"),
        "business_criticality": task.get("business_criticality"),
        "time_allocation": task.get("time_allocation"),
        "ai_assistance": task.get("ai_assistance"),
        "confidence_score": task.get("confidence_score"),
        "manual_notes": str(task.get("manual_notes", "")).strip() or None,
        "selected": task.get("selected"),
        "sort_order": task.get("sort_order"),
        "source": task.get("source"),
    }


def compute_tasks_content_hash(tasks: list[AssessmentTask | dict[str, Any]]) -> str:
    signatures = sorted(
        [_task_signature(t) for t in tasks],
        key=lambda item: (item.get("sort_order", 0), item.get("title", "")),
    )
    canonical = json.dumps(signatures, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
