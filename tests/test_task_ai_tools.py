"""Task-specific AI tool recommendation filtering. Uses fixtures, not a live model."""

from promppts.TaskAIToolsService import SYSTEM_PROMPT
from app.services.report_generator import build_toolkit_from_analyses
from app.services.task_ai_tools import apply_tool_recommendations, prepare_tool_recommendations


def _tool(
    name: str,
    *,
    access_class: str,
    why: str,
    how: str,
    connection: str,
    feasibility: str = "self_serve",
    cost_band: str = "freemium",
) -> dict:
    return {
        "name": name,
        "access_class": access_class,
        "why_this_tool": why,
        "how_to_use": how,
        "task_connection": connection,
        "expected_benefit": f"Speeds the work described for {name}.",
        "starting_point": f"Open {name} and start from the task deliverable.",
        "limitations": "Confirm you are allowed to upload the source material before you rely on the output.",
        "cost_band": cost_band,
        "pricing_note": "Public pricing varies.",
        "feasibility": feasibility,
        "fit_description": why,
        "market_note": "Used by practitioners for this kind of work.",
        "pros": ["Fits this component", "Reduces manual drafting"],
        "cons": ["Needs a human review", "Access depends on the plan"],
    }


def _task(task_id: str, title: str, component: str, tools: list[dict], description: str = "") -> dict:
    return {
        "task_id": task_id,
        "title": title,
        "components": [
            {
                "name": component,
                "description": description or component,
                "tools": tools,
            }
        ],
    }


def test_prompt_requires_task_specific_tools_and_forbids_a_universal_list():
    assert "access_class" in SYSTEM_PROMPT
    assert "enterprise" in SYSTEM_PROMPT
    assert "external" in SYSTEM_PROMPT
    assert "Do not repeat the same generic tool list" in SYSTEM_PROMPT
    assert "job title alone" in SYSTEM_PROMPT


def test_succession_task_keeps_talent_tools_and_drops_unrelated_slides():
    prepared = prepare_tool_recommendations(
        [
            _task(
                "succ-1",
                "Succession planning",
                "Successor identification",
                [
                    _tool(
                        "Eightfold AI",
                        access_class="enterprise",
                        why="Eightfold AI supports succession planning by ranking successor readiness.",
                        how="Load the succession planning roster into Eightfold AI, compare successor skills, and review the shortlist before any talent decision.",
                        connection="Successor identification for the succession plan",
                        feasibility="org_must_enable",
                        cost_band="enterprise",
                    ),
                    _tool(
                        "Gamma",
                        access_class="external",
                        why="Gamma makes slides look polished for a general presentation.",
                        how="Paste notes into Gamma and generate a slide deck about a general topic with no workforce deliverable.",
                        connection="A generic slide deck",
                    ),
                ],
            )
        ]
    )
    names = [tool["name"] for tool in prepared[0]["components"][0]["tools"]]
    assert names == ["Eightfold AI"]
    assert prepared[0]["components"][0]["tools"][0]["access_class"] == "enterprise"


def test_training_audit_automation_and_presentation_tasks_stay_separate():
    prepared = prepare_tool_recommendations(
        [
            _task(
                "train-1",
                "Training needs analysis",
                "Skill gap review",
                [
                    _tool(
                        "Julius AI",
                        access_class="external",
                        why="Julius AI examines the training needs analysis dataset for skill gap patterns.",
                        how="Upload the authorized training needs export to Julius AI, ask for skill gap patterns, and check every figure against the source file.",
                        connection="Skill gap review for training needs",
                    )
                ],
            ),
            _task(
                "audit-1",
                "ISO audit preparation",
                "Evidence checklist",
                [
                    _tool(
                        "NotebookLM",
                        access_class="external",
                        why="NotebookLM organizes the ISO audit preparation evidence into a checklist.",
                        how="Add the audit evidence files to NotebookLM, ask which ISO clauses lack proof, and verify each gap against the original record.",
                        connection="Evidence checklist for the ISO audit",
                    )
                ],
            ),
            _task(
                "auto-1",
                "Workflow automation",
                "Agent handoff",
                [
                    _tool(
                        "Power Automate",
                        access_class="enterprise",
                        why="Power Automate connects the workflow automation steps that are repeated every day.",
                        how="Build a Power Automate flow for the workflow automation handoff, test it on one record, and keep an exception path for failures.",
                        connection="Agent handoff inside the workflow automation",
                        feasibility="org_must_enable",
                    )
                ],
            ),
            _task(
                "deck-1",
                "Executive presentation",
                "Slide narrative",
                [
                    _tool(
                        "Gamma",
                        access_class="external",
                        why="Gamma turns the executive presentation outline into a slide narrative.",
                        how="Paste the approved executive presentation outline into Gamma, generate the slide narrative, and edit the claims before the meeting.",
                        connection="Slide narrative for the executive presentation",
                    )
                ],
            ),
        ]
    )
    by_id = {item["task_id"]: item["components"][0]["tools"][0]["name"] for item in prepared}
    assert by_id == {
        "train-1": "Julius AI",
        "audit-1": "NotebookLM",
        "auto-1": "Power Automate",
        "deck-1": "Gamma",
    }


def test_technical_task_drops_hr_tool_when_a_relevant_tool_exists():
    prepared = prepare_tool_recommendations(
        [
            _task(
                "eng-1",
                "Debug API integration",
                "Error log triage",
                [
                    _tool(
                        "Cursor",
                        access_class="external",
                        why="Cursor helps debug the API integration from the error log triage notes.",
                        how="Open the failing API integration in Cursor, paste the error log triage excerpt, and review the proposed change before you commit it.",
                        connection="Error log triage for the API integration",
                    ),
                    _tool(
                        "Workday Illuminate",
                        access_class="enterprise",
                        why="Workday Illuminate supports succession planning for leadership roles.",
                        how="Open the succession module and compare leadership readiness scores for the annual talent review.",
                        connection="Leadership succession review",
                        feasibility="org_must_enable",
                        cost_band="enterprise",
                    ),
                ],
            )
        ]
    )
    names = [tool["name"] for tool in prepared[0]["components"][0]["tools"]]
    assert names == ["Cursor"]


def test_same_tool_can_serve_two_tasks_with_different_guidance():
    shared_bits = dict(
        access_class="external",
        feasibility="self_serve",
        cost_band="freemium",
    )
    prepared = prepare_tool_recommendations(
        [
            _task(
                "a",
                "Succession planning",
                "Successor brief",
                [
                    _tool(
                        "Claude",
                        why="Claude drafts the succession planning successor brief from notes you already trust.",
                        how="Paste the succession planning criteria into Claude, ask for a successor brief, and correct any claim that is not in the notes.",
                        connection="Successor brief",
                        **shared_bits,
                    )
                ],
            ),
            _task(
                "b",
                "Executive presentation",
                "Speaker notes",
                [
                    _tool(
                        "Claude",
                        why="Claude drafts speaker notes for the executive presentation from the approved outline.",
                        how="Paste the executive presentation outline into Claude, ask for speaker notes, and remove any point that was not approved.",
                        connection="Speaker notes",
                        **shared_bits,
                    )
                ],
            ),
        ]
    )
    first = prepared[0]["components"][0]["tools"][0]["how_to_use"]
    second = prepared[1]["components"][0]["tools"][0]["how_to_use"]
    assert "succession planning" in first
    assert "executive presentation" in second
    assert first != second


def test_duplicates_placeholders_and_malformed_rows_are_dropped():
    long_why = "This tool supports succession planning by comparing successor evidence."
    long_how = "Use it on the succession planning roster and check every successor suggestion against the source record."
    prepared = prepare_tool_recommendations(
        [
            "not-a-task",
            {"title": "Missing id", "components": []},
            _task(
                "succ-2",
                "Succession planning",
                "Successor identification",
                [
                    _tool(
                        "Claude",
                        access_class="external",
                        why=long_why,
                        how=long_how,
                        connection="Successor identification",
                    ),
                    _tool(
                        "Claude",
                        access_class="external",
                        why=long_why,
                        how=long_how + " Review the second copy too.",
                        connection="Successor identification",
                    ),
                    {"name": "AI Tool", "why_this_tool": long_why, "how_to_use": long_how},
                    {"name": "Tiny", "why_this_tool": "short", "how_to_use": "also short"},
                ],
            ),
        ]
    )
    assert len(prepared) == 1
    assert [tool["name"] for tool in prepared[0]["components"][0]["tools"]] == ["Claude"]


def test_access_class_falls_back_from_rollout_not_from_brand():
    prepared = prepare_tool_recommendations(
        [
            _task(
                "ops-1",
                "Workflow automation",
                "Approval routing",
                [
                    {
                        "name": "ServiceNow Now Assist",
                        "why_this_tool": "ServiceNow Now Assist routes the workflow automation approvals.",
                        "how_to_use": "Configure the workflow automation approval step in ServiceNow Now Assist and test one approval before enabling it for the team.",
                        "task_connection": "Approval routing",
                        "feasibility": "org_must_enable",
                        "cost_band": "paid_team",
                        "pros": ["Fits approval routing"],
                        "cons": ["Needs an admin"],
                    }
                ],
            )
        ]
    )
    tool = prepared[0]["components"][0]["tools"][0]
    assert tool["access_class"] == "enterprise"


def test_recommendations_attach_only_to_the_matching_component():
    components = [
        {"name": "Successor identification", "description": "Rank people"},
        {"name": "Slide narrative", "description": "Write the deck"},
    ]
    updated, names = apply_tool_recommendations(
        components,
        [
            {
                "name": "Successor identification",
                "tools": [{"name": "Eightfold AI"}],
            }
        ],
    )
    assert names == ["Eightfold AI"]
    assert updated[0]["tools"] == [{"name": "Eightfold AI"}]
    assert updated[1]["tools"] == []
    assert updated[1]["description"] == "Write the deck"


def test_toolkit_uses_task_guidance_and_does_not_invent_tools():
    analyses = [
        {
            "task_title": "Succession planning",
            "category": "BLEND",
            "reason": "Human judgment remains on the final slate.",
            "recommended_tools": [],
            "components": [
                {
                    "name": "Successor identification",
                    "tools": [
                        {
                            "name": "Eightfold AI",
                            "access_class": "enterprise",
                            "why_this_tool": "Ranks successor readiness for this succession planning slate.",
                            "how_to_use": "Compare the slate, then review every name yourself.",
                            "starting_point": "Open the succession workspace.",
                            "limitations": "Needs an HR admin to enable it.",
                        }
                    ],
                }
            ],
        }
    ]
    tools = build_toolkit_from_analyses(analyses)
    assert [tool["name"] for tool in tools] == ["Eightfold AI"]
    assert tools[0]["category"] == "Enterprise AI Tools"
    assert "successor readiness" in tools[0]["use_case"]
    assert tools[0]["task_links"][0]["how_to_use"].startswith("Compare the slate")
    assert all(tool["name"] != "ChatGPT" for tool in tools)


def test_empty_analysis_does_not_add_generic_fallback_tools():
    assert build_toolkit_from_analyses([]) == []
