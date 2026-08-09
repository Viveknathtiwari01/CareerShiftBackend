import pytest

from app.services.report_version import (
    format_report_version,
    next_report_version,
    revision_number,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", 1),
        ("3", 3),
        ("1.0", 1),
        ("1.1", 2),
        ("1.5", 6),
        ("1.0.0.1.1.1.1.1", 7),
    ],
)
def test_revision_number_parses_legacy_values(raw, expected):
    assert revision_number(raw) == expected


def test_format_report_version_is_user_friendly():
    assert format_report_version("1.0.0.1.1.1.1.1") == "7"
    assert format_report_version("3") == "3"


def test_next_report_version_increments_cleanly():
    assert next_report_version("1") == "2"
    assert next_report_version("1.0.0.1.1.1.1.1") == "8"
