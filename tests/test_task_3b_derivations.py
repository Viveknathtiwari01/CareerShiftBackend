"""Tests for 3B server-side derivations."""

from types import SimpleNamespace

from app.services.task_3b_derivations import (
    derive_feasibility,
    derive_importance,
    enrich_cost_of_staying_as_is,
    merge_market_reality,
    recommended_build_task_id,
    resolve_feasibility_note,
)


def test_derive_importance_from_business_criticality():
    task = SimpleNamespace(business_criticality="critical")
    assert derive_importance(task) == "Mission Critical"


def test_derive_feasibility_build_stays_human_led():
    tier, note = derive_feasibility("BUILD", [])
    assert tier == "stays_human_led"
    assert "human" in note.lower()


def test_derive_feasibility_picks_most_actionable_tier():
    components = [
        {
            "is_automatable": True,
            "tools": [
                {"feasibility": "org_must_enable"},
                {"feasibility": "self_serve"},
            ],
        }
    ]
    tier, _ = derive_feasibility("BLEND", components)
    assert tier == "self_serve"


def test_enrich_cost_of_staying_adds_annual_hours():
    result = enrich_cost_of_staying_as_is(
        {"type": "reclaimable_time", "narrative": "Time sink"},
        weekly_hours=5.0,
    )
    assert result["annual_hours"] == 260.0


def test_merge_market_reality_from_nested_and_legacy_pivot():
    merged = merge_market_reality(
        {
            "market_reality": {"trend_text": "Role shifting toward AI-assisted workflows."},
            "pivot_roles": [{"name": "Ops Analyst", "transfer_strength": "High", "reuses": "BUILD skills", "note": "Adjacent"}],
        }
    )
    assert "AI-assisted" in merged["trend_text"]
    assert len(merged["pivot_roles"]) == 1


def test_resolve_feasibility_note_prefers_llm_text():
    tier, note = resolve_feasibility_note(
        "BLEND",
        [{"is_automatable": True, "tools": [{"feasibility": "self_serve"}]}],
        "Power BI is likely already licensed — start with a dashboard template.",
    )
    assert tier == "self_serve"
    assert "Power BI" in note


def test_resolve_feasibility_note_falls_back_when_llm_empty():
    tier, note = resolve_feasibility_note("BUILD", [], None)
    assert tier == "stays_human_led"
    assert note


def test_recommended_build_task_id_by_hours_and_importance():
    rows = [
        SimpleNamespace(
            category="BUILD",
            task_id="aaa",
            task=SimpleNamespace(title="Low", hours_per_week=2, business_criticality="low"),
        ),
        SimpleNamespace(
            category="BUILD",
            task_id="bbb",
            task=SimpleNamespace(title="High", hours_per_week=5, business_criticality="critical"),
        ),
    ]
    assert recommended_build_task_id(rows, task_for_row=lambda r: r.task) == "bbb"
