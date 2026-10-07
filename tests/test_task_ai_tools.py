"""Parse AI tool recommendations without a live model call."""

from __future__ import annotations

import json

import pytest

from app.services.task_ai_tools import _parse_tools_json


def _payload() -> dict:
    return {
        "tasks": [
            {
                "task_id": "task-1",
                "title": "Review applications",
                "components": [
                    {
                        "name": "Screen resumes",
                        "tools": [
                            {
                                "name": "Greenhouse",
                                "pros": ["Structured scorecards"],
                                "cons": ["Needs a company account"],
                            }
                        ],
                    }
                ],
            }
        ]
    }


def test_parse_tools_json_with_preamble_and_fence():
    text = f"Here are the tools:\n```json\n{json.dumps(_payload())}\n```\nDone."
    parsed = _parse_tools_json(text)
    assert parsed["tasks"][0]["task_id"] == "task-1"
    assert parsed["tasks"][0]["components"][0]["tools"][0]["name"] == "Greenhouse"


def test_parse_tools_json_trailing_comma_and_newline():
    text = json.dumps(_payload()).replace(
        "Structured scorecards",
        "Structured\nscorecards",
    )
    text = text[:-1] + ",}"
    parsed = _parse_tools_json(text)
    assert parsed["tasks"][0]["components"][0]["tools"][0]["pros"] == ["Structured\nscorecards"]


def test_parse_tools_json_rejects_non_object():
    with pytest.raises(Exception):
        _parse_tools_json("not json at all")
