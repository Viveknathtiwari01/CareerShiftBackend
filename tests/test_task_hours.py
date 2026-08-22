"""Tests for 3B task hours calculations."""

from app.services.task_hours import (
    annual_hours_from_weekly,
    compute_hours_summary,
    effective_task_hours,
)


def test_effective_task_hours_maps_review_buckets():
    assert effective_task_hours({"time_allocation": 0.25, "hours_per_week": 9}) == 1.0
    assert effective_task_hours({"time_allocation": 8.0, "hours_per_week": 9}) == 10.0
    assert effective_task_hours({"hours_per_week": 9}) == 9.0


def test_annual_hours_from_weekly():
    assert annual_hours_from_weekly(22) == 1144.0


def test_compute_hours_summary():
    tasks = [
        ({"time_allocation": 8.0}, "BUILD"),
        ({"time_allocation": 4.0}, "BLEND"),
        ({"time_allocation": 0.25}, "BOT"),
    ]
    summary = compute_hours_summary(tasks)
    assert summary["BUILD"]["weekly_hours"] == 10.0
    assert summary["BLEND"]["weekly_hours"] == 8.0
    assert summary["BOT"]["weekly_hours"] == 1.0
    assert summary["total"]["weekly_hours"] == 19.0
    assert summary["BUILD"]["annual_hours"] == 520.0
