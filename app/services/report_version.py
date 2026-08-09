"""Helpers for career report revision numbering and display."""

from __future__ import annotations

REPORT_VERSION = "1"


def revision_number(version: str | None) -> int:
    """Parse stored report_version into a simple 1-based revision number."""
    value = (version or REPORT_VERSION).strip()
    if value.isdigit():
        return max(1, int(value))

    parts = value.split(".")
    numeric_parts = [part for part in parts if part.isdigit()]
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        major, minor = int(parts[0]), int(parts[1])
        if major == 1:
            return max(1, minor + 1)

    if parts and parts[0] == "1":
        return max(1, len(parts) - 1)

    return max(1, len(numeric_parts) or 1)


def format_report_version(version: str | None) -> str:
    """User-facing label, e.g. '3'."""
    return str(revision_number(version))


def next_report_version(current: str | None) -> str:
    return str(revision_number(current) + 1)
