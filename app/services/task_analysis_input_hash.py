"""Stable fingerprint for locking 3B analysis to assessment inputs."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.models.assessment_task import AssessmentTask
from app.services.task_content_hash import compute_tasks_content_hash


def _compact_competency_snapshot(competency_final_output: dict[str, Any] | None) -> dict[str, Any]:
    if not competency_final_output:
        return {}
    competencies = []
    for item in competency_final_output.get("competencies") or []:
        if isinstance(item, dict):
            competencies.append(
                {
                    "name": item.get("name"),
                    "category": item.get("category"),
                    "importance": item.get("importance"),
                    "expected_level": item.get("expected_level"),
                }
            )
    return {
        "profession_summary": competency_final_output.get("profession_summary"),
        "competencies": sorted(competencies, key=lambda c: str(c.get("name", ""))),
    }


def compute_task_analysis_input_hash(
    competency_final_output: dict[str, Any] | None,
    selected_tasks: list[AssessmentTask],
) -> str:
    """Hash competency + reviewed tasks — not live profile fields.

    Profile updates alone do not invalidate 3B; re-assessment (new competency/tasks) does.
    """
    payload = {
        "competency": _compact_competency_snapshot(competency_final_output),
        "tasks_hash": compute_tasks_content_hash(selected_tasks),
    }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
