"""Tests verifying dynamic AI tool generation across diverse industries and domains:
1. Healthcare / Learning & Development / HR (Assistant Manager, Transformation, AI & Learning)
2. Financial Services / Corporate Finance (Senior Financial Analyst)
3. Manufacturing / Supply Chain & Procurement (Supply Chain Operations Manager)
"""

from uuid import uuid4
import pytest

from app.services.task_ai_tools import (
    canonical_product_id,
    prepare_tool_recommendations,
    apply_tool_recommendations,
)
from app.services.report_generator import (
    ReportGeneratorInput,
    generate_career_intelligence_report,
)


def _tool(
    name: str,
    *,
    access_class: str,
    why: str,
    how: str,
    connection: str,
    pros: list[str] | None = None,
    cons: list[str] | None = None,
    task_fit_rank: int = 1,
    cost_band: str = "freemium",
) -> dict:
    return {
        "name": name,
        "access_class": access_class,
        "task_fit_rank": task_fit_rank,
        "task_fit_reason": f"Primary recommendation for {connection}.",
        "why_this_tool": why,
        "how_to_use": how,
        "task_connection": connection,
        "expected_benefit": f"Substantially accelerates {connection} with high accuracy.",
        "starting_point": f"Configure {name} workspace and import source datasets.",
        "limitations": "Ensure organizational governance policies are verified before processing sensitive data.",
        "cost_band": cost_band,
        "pricing_note": "Subscription pricing based on user tier or enterprise contract.",
        "feasibility": "org_must_enable" if access_class == "enterprise" else "self_serve",
        "fit_description": why,
        "market_note": "Widely utilized across modern organizations for this deliverable.",
        "pros": pros or ["High domain accuracy for this deliverable", "Reduces manual compilation time"],
        "cons": cons or ["Requires initial data integration setup", "Human expert verification required"],
    }


def _task(task_id: str, title: str, components: list[dict]) -> dict:
    return {
        "task_id": task_id,
        "title": title,
        "components": components,
    }


# ==============================================================================
# 1. HEALTHCARE / LEARNING & DEVELOPMENT / HR DOMAIN TEST
# Role: Assistant Manager, Transformation, AI & Learning
# Specialization: Leadership Development & Employee Engagement
# ==============================================================================

def test_healthcare_ld_transformation_generates_valid_specialist_tools():
    """Verify that a Healthcare L&D Transformation leader receives healthcare/HR/L&D AI tools,
    never developer tools, and maintains 2-3 distinct tools per component with Pros and Cons."""
    raw_tasks = [
        _task(
            "hc-ld-1",
            "Training Needs Analysis & Clinical Competency Assessment",
            [
                {
                    "name": "Clinical Skill Gap Modeling",
                    "description": "Analyzing clinical competency benchmarks and identifying hospital staff skill gaps.",
                    "tools": [
                        _tool(
                            "Visier",
                            access_class="enterprise",
                            why="Visier enables workforce analytics to uncover clinical skill gaps across healthcare departments.",
                            how="Upload hospital clinical competency metrics into Visier and run skill gap heatmaps.",
                            connection="Clinical skill gap modeling for healthcare staff",
                            pros=["Comprehensive healthcare workforce analytics", "Identifies hidden clinical skill deficits"],
                            cons=["Requires enterprise HRIS data integration", "Requires hospital data governance review"],
                            task_fit_rank=1,
                        ),
                        _tool(
                            "Microsoft Power BI Copilot",
                            access_class="enterprise",
                            why="Power BI Copilot analyzes healthcare training survey datasets and builds interactive competency dashboards.",
                            how="Connect the clinical assessment dataset to Power BI and prompt Copilot for skill distribution charts.",
                            connection="Clinical competency assessment reporting",
                            pros=["Automated DAX formulas and visual dashboards", "Integrates seamlessly with Microsoft 365"],
                            cons=["Requires Power BI Premium capacity", "Clinical taxonomy requires manual alignment"],
                            task_fit_rank=2,
                        ),
                        _tool(
                            "Julius AI",
                            access_class="external",
                            why="Julius AI performs statistical analysis on clinical staff survey data and skill gap patterns.",
                            how="Upload de-identified clinical survey spreadsheets to Julius AI and request variance regressions.",
                            connection="Statistical skill gap modeling",
                            pros=["Rapid Python-backed statistical modeling", "Instant chart and graph generation from prompts"],
                            cons=["Requires strict de-identification of patient/staff data", "Self-serve export limits"],
                            task_fit_rank=3,
                        ),
                    ],
                },
                {
                    "name": "Curriculum Alignment & AI Learning Design",
                    "description": "Designing adaptive learning paths and training modules for healthcare teams.",
                    "tools": [
                        _tool(
                            "360Learning AI",
                            access_class="external",
                            why="360Learning AI generates collaborative clinical micro-learning courses and quizzes.",
                            how="Input clinical guidelines into 360Learning AI to generate structured learning modules for medical staff.",
                            connection="Curriculum alignment and learning design",
                            pros=["Rapid clinical module generation", "Built-in peer collaboration features"],
                            cons=["Clinical accuracy requires medical director signoff", "Custom interactive simulations limited"],
                            task_fit_rank=1,
                        ),
                        _tool(
                            "Cornerstone Galaxy AI",
                            access_class="enterprise",
                            why="Cornerstone Galaxy AI maps clinical competencies to curated healthcare learning content.",
                            how="Activate Cornerstone skills ontology and map nursing and physician competency matrices.",
                            connection="Enterprise learning curriculum alignment",
                            pros=["Deep enterprise LMS capability and compliance tracking", "Automated skill-to-content matching"],
                            cons=["High enterprise procurement cost", "Complex configuration across hospital units"],
                            task_fit_rank=2,
                        ),
                    ],
                },
            ],
        ),
        _task(
            "hc-ld-2",
            "Leadership Development & Kirkpatrick Evaluation",
            [
                {
                    "name": "Leadership Simulation Workshop Design",
                    "description": "Creating scenario-based leadership simulations for clinical leaders and nurse managers.",
                    "tools": [
                        _tool(
                            "Sana AI",
                            access_class="enterprise",
                            why="Sana AI builds interactive leadership scenarios and personalized learning journeys for healthcare leaders.",
                            how="Input leadership case studies into Sana AI to create interactive branching role-plays.",
                            connection="Leadership simulation scenario creation",
                            pros=["Adaptive learning paths tailored to learner pace", "Rich multimedia and roleplay creation"],
                            cons=["Enterprise plan required for custom integrations", "Requires expert curation of medical dilemmas"],
                            task_fit_rank=1,
                        ),
                        _tool(
                            "Synthesia",
                            access_class="external",
                            why="Synthesia produces AI avatar video briefings for healthcare leadership transformation announcements.",
                            how="Paste approved executive briefing scripts into Synthesia to generate training videos for distributed hospital staff.",
                            connection="Leadership video modules and briefings",
                            pros=["Studio-quality training videos without cameras or actors", "Fast multi-lingual translation for diverse staff"],
                            cons=["Avatars can feel slightly synthetic for sensitive emotional topics", "Video editing flexibility is constrained"],
                            task_fit_rank=2,
                        ),
                    ],
                },
                {
                    "name": "Kirkpatrick Impact & Engagement Analytics",
                    "description": "Measuring Level 1-4 training effectiveness, employee engagement, and behavioral shift.",
                    "tools": [
                        _tool(
                            "Qualtrics AI",
                            access_class="enterprise",
                            why="Qualtrics AI automates post-training sentiment analysis and evaluates employee engagement shifts.",
                            how="Deploy Kirkpatrick evaluation surveys through Qualtrics and use Text iQ to detect morale patterns.",
                            connection="Kirkpatrick evaluation and staff engagement measurement",
                            pros=["Automated sentiment extraction and topic clustering", "Statistically validated employee experience benchmarks"],
                            cons=["Enterprise license cost", "Complex survey setup for large hospital systems"],
                            task_fit_rank=1,
                        ),
                        _tool(
                            "Eightfold AI",
                            access_class="enterprise",
                            why="Eightfold AI tracks talent mobility and leadership bench strength post-training.",
                            how="Review leadership succession pipelines and measure promotion velocity of program graduates.",
                            connection="Succession readiness and leadership talent architecture",
                            pros=["Deep skills intelligence and succession modeling", "Reduces bias in leadership talent identification"],
                            cons=["Requires comprehensive HR data integration", "Long implementation timeline"],
                            task_fit_rank=2,
                        ),
                    ],
                },
            ],
        ),
    ]

    prepared = prepare_tool_recommendations(raw_tasks)
    assert len(prepared) == 2

    # Check Task 1
    t1 = prepared[0]
    assert len(t1["components"]) == 2
    comp1_tools = t1["components"][0]["tools"]
    comp2_tools = t1["components"][1]["tools"]

    assert len(comp1_tools) == 3
    assert [tool["name"] for tool in comp1_tools] == ["Visier", "Microsoft Power BI Copilot", "Julius AI"]
    assert len(comp2_tools) == 2
    assert [tool["name"] for tool in comp2_tools] == ["360Learning AI", "Cornerstone Galaxy AI"]

    # Verify every tool has at least 2 pros and 2 cons
    for comp in t1["components"]:
        for tool in comp["tools"]:
            assert len(tool.get("pros", [])) >= 2
            assert len(tool.get("cons", [])) >= 2
            assert tool["access_class"] in {"enterprise", "external"}

    # Test full report generation pipeline for this Healthcare L&D profile
    report_input = ReportGeneratorInput(
        assessment_id=uuid4(),
        profile={
            "job_title": "Assistant Manager, Transformation, AI & Learning",
            "industry": "Healthcare",
            "business_function": "Human Resources",
            "domain": "Learning & Development",
            "specialization": "Leadership Development & Employee Engagement",
            "experience_years": 7,
            "salary": "$95,000",
            "digital_skills": ["LMS", "Workday", "Survey Analytics", "Power BI"],
            "ai_frequency": "daily",
            "ai_tools": ["ChatGPT", "Power BI Copilot"],
            "ai_comfort_level": 8,
        },
        tasks=[
            {
                "task_id": uuid4(),
                "title": "Training Needs Analysis & Clinical Competency Assessment",
                "category": "Analysis",
                "hours_per_week": 12,
                "business_criticality": "High",
                "ai_assistance": "sometimes",
                "confidence_score": 85,
                "category_3b": "BLEND",
            },
            {
                "task_id": uuid4(),
                "title": "Leadership Development & Kirkpatrick Evaluation",
                "category": "Program Design",
                "hours_per_week": 14,
                "business_criticality": "Critical",
                "ai_assistance": "never",
                "confidence_score": 90,
                "category_3b": "BOT",
            },
        ],
        analyses=[
            {
                "task_id": uuid4(),
                "task_title": "Training Needs Analysis & Clinical Competency Assessment",
                "category": "BLEND",
                "rationale": "AI analyzes survey data and builds dashboards while human aligns clinical strategy.",
                "reason": "Requires healthcare clinical understanding and stakeholder buy-in.",
                "next_actions": ["Deploy Visier analytics", "Build Power BI competency dashboard", "Conduct gap review"],
                "auto_potential": 60,
                "recommended_tools": ["Visier", "Microsoft Power BI Copilot", "Julius AI"],
                "components": t1["components"],
            },
            {
                "task_id": uuid4(),
                "task_title": "Leadership Development & Kirkpatrick Evaluation",
                "category": "BOT",
                "rationale": "Repetitive pulse survey sentiment and simulation module drafting can be automated.",
                "reason": "Standardized Kirkpatrick Level 1 and 2 surveys follow algorithmic evaluation.",
                "next_actions": ["Launch Qualtrics AI surveys", "Draft leadership scenarios with Sana AI", "Track bench strength with Eightfold"],
                "auto_potential": 75,
                "recommended_tools": ["Sana AI", "Synthesia", "Qualtrics AI", "Eightfold AI"],
                "components": prepared[1]["components"],
            },
        ],
        competencies=[
            {
                "name": "Healthcare Leadership Development",
                "category": "Business",
                "importance": "High",
                "expected_level": "Advanced",
            },
            {
                "name": "Kirkpatrick Program Evaluation",
                "category": "Technical",
                "importance": "High",
                "expected_level": "Advanced",
            },
        ],
        profession_summary="Healthcare L&D leader driving AI-assisted clinical transformation and leadership development.",
    )

    report = generate_career_intelligence_report(report_input)

    # Verify report AI toolkit contains healthcare/HR tools, no developer tools
    toolkit_names = [item.name for item in report.ai_toolkit]
    assert "Visier" in toolkit_names
    assert "Qualtrics AI" in toolkit_names
    assert "Sana AI" in toolkit_names
    assert "Eightfold AI" in toolkit_names
    # Developer tools must NOT be present
    assert "Cursor" not in toolkit_names
    assert "GitHub Copilot" not in toolkit_names
    assert "Postman AI" not in toolkit_names

    # Verify Pros & Cons survived in report toolkit
    for item in report.ai_toolkit:
        assert len(item.pros) >= 2 or any(link.pros for link in item.task_links)
        assert len(item.cons) >= 2 or any(link.cons for link in item.task_links)


# ==============================================================================
# 2. FINANCIAL SERVICES / CORPORATE FINANCE DOMAIN TEST
# Role: Senior Financial Analyst (Valuation & Financial Modeling)
# ==============================================================================

def test_financial_services_generates_valid_finance_ai_tools():
    """Verify that a Senior Financial Analyst receives market-standard Finance AI tools."""
    raw_tasks = [
        _task(
            "fin-1",
            "Financial Modeling & DCF Valuation",
            [
                {
                    "name": "DCF Scenario Modeling",
                    "description": "Constructing discounted cash flow valuation models and sensitivity matrices.",
                    "tools": [
                        _tool(
                            "FinChat.io",
                            access_class="external",
                            why="FinChat.io verifies financial modeling assumptions against SEC filings and consensus data.",
                            how="Query FinChat.io for peer enterprise multiples and historical free cash flow growth rates.",
                            connection="DCF scenario modeling and valuation assumptions",
                            pros=["Direct citations to official 10-K and 10-Q SEC filings", "Fast peer multiple comparisons"],
                            cons=["Coverage limited to public equities", "Requires financial judgment on terminal growth rates"],
                        ),
                        _tool(
                            "Microsoft 365 Copilot",
                            access_class="enterprise",
                            why="Copilot in Excel generates dynamic sensitivity tables and formula debugging for financial models.",
                            how="Open the valuation workbook in Excel, prompt Copilot to run multi-variable WACC sensitivity analysis.",
                            connection="Excel valuation modeling and formula generation",
                            pros=["Native integration within Excel models", "Automates complex multi-variable scenario tables"],
                            cons=["Complex circular model references may hallucinate", "Requires enterprise Microsoft 365 Copilot license"],
                        ),
                    ],
                },
                {
                    "name": "Audit Sample Verification & Compliance",
                    "description": "Reconciling ledger entries and auditing transaction workpapers.",
                    "tools": [
                        _tool(
                            "DataSnipper AI",
                            access_class="enterprise",
                            why="DataSnipper AI cross-references financial statement figures to source contracts and invoices.",
                            how="Load audited financial statements into DataSnipper and run Document Matching against bank confirmations.",
                            connection="Audit sample verification and workpaper cross-referencing",
                            pros=["Exceptional accuracy in tying numbers back to source PDFs", "Drastically cuts manual audit sampling time"],
                            cons=["Enterprise firm deployment required", "Scanned handwritten receipts require OCR checking"],
                        ),
                        _tool(
                            "MindBridge AI",
                            access_class="enterprise",
                            why="MindBridge AI scans the general ledger for unusual journal entries and anomalous transactions.",
                            how="Import the general ledger into MindBridge and review high-risk anomaly scores.",
                            connection="Financial transaction anomaly detection",
                            pros=["Advanced anomaly detection across 100% of journal entries", "Compliant with international auditing standards"],
                            cons=["High enterprise cost", "Initial false positive triage requires senior auditor review"],
                        ),
                    ],
                },
            ],
        )
    ]

    prepared = prepare_tool_recommendations(raw_tasks)
    assert len(prepared) == 1
    t1 = prepared[0]
    names_c1 = [t["name"] for t in t1["components"][0]["tools"]]
    names_c2 = [t["name"] for t in t1["components"][1]["tools"]]

    assert "FinChat.io" in names_c1
    assert "Microsoft 365 Copilot" in names_c1
    assert "DataSnipper AI" in names_c2
    assert "MindBridge AI" in names_c2


# ==============================================================================
# 3. MANUFACTURING / SUPPLY CHAIN & PROCUREMENT DOMAIN TEST
# Role: Supply Chain Operations Manager (Demand Forecasting & Vendor Risk)
# ==============================================================================

def test_supply_chain_operations_generates_valid_logistics_ai_tools():
    """Verify that a Supply Chain Operations Manager receives supply chain & procurement AI tools."""
    raw_tasks = [
        _task(
            "sc-1",
            "Demand Planning & Inventory Optimization",
            [
                {
                    "name": "Demand Forecast Variance Analysis",
                    "description": "Forecasting SKU-level demand patterns and optimizing regional safety stocks.",
                    "tools": [
                        _tool(
                            "Blue Yonder AI",
                            access_class="enterprise",
                            why="Blue Yonder AI forecasts consumer demand by incorporating weather, promotions, and market trends.",
                            how="Ingest point-of-sale data into Blue Yonder AI demand planning module to recalculate safety stock buffers.",
                            connection="Demand forecast variance and replenishment planning",
                            pros=["Machine-learning demand sensing with external weather/macro signals", "Automated replenishment recommendations"],
                            cons=["Heavy ERP and data pipeline configuration", "Requires significant organizational training"],
                        ),
                        _tool(
                            "Kinaxis Maestro AI",
                            access_class="enterprise",
                            why="Kinaxis Maestro AI models multi-tier supply chain disruption scenarios in real-time.",
                            how="Run what-if scenario simulations on supplier port congestion in Kinaxis to assess lead-time impact.",
                            connection="Supply chain disruption and safety stock scenario modeling",
                            pros=["Rapid concurrent supply-demand rebalancing", "End-to-end multi-tier supply network visibility"],
                            cons=["Enterprise procurement only", "High tier pricing"],
                        ),
                    ],
                },
                {
                    "name": "Supplier Risk & Contract Review",
                    "description": "Evaluating supplier delivery reliability and monitoring contract terms.",
                    "tools": [
                        _tool(
                            "Coupa AI",
                            access_class="enterprise",
                            why="Coupa AI monitors procurement spend and assesses vendor delivery risk across global supply networks.",
                            how="Analyze supplier scorecards in Coupa to identify high-risk delivery bottlenecks before renewal.",
                            connection="Supplier risk assessment and procurement analytics",
                            pros=["Community intelligence benchmarking across billions in spend", "Early warning risk alerts for distressed vendors"],
                            cons=["Requires enterprise Coupa BSM suite", "Legacy vendor onboarding may take time"],
                        ),
                        _tool(
                            "Ironclad AI",
                            access_class="enterprise",
                            why="Ironclad AI extracts SLA penalties and force majeure terms from supplier master service agreements.",
                            how="Upload supplier contracts to Ironclad AI and query for lead-time guarantee clauses and indemnity caps.",
                            connection="Supplier contract clause review and risk mitigation",
                            pros=["Instant redlining and key clause extraction", "Automated contract metadata repository"],
                            cons=["Complex legal edge cases still need legal counsel review", "Integration required with ERP/CRM"],
                        ),
                    ],
                },
            ],
        )
    ]

    prepared = prepare_tool_recommendations(raw_tasks)
    assert len(prepared) == 1
    t1 = prepared[0]
    names_c1 = [t["name"] for t in t1["components"][0]["tools"]]
    names_c2 = [t["name"] for t in t1["components"][1]["tools"]]

    assert "Blue Yonder AI" in names_c1
    assert "Kinaxis Maestro AI" in names_c1
    assert "Coupa AI" in names_c2
    assert "Ironclad AI" in names_c2


# ==============================================================================
# 4. RESILIENCE TEST: CHANGE MANAGEMENT & TEAM MEETINGS DEFENSIVE BACKFILL
# ==============================================================================

def test_change_management_and_team_meetings_backfill_safely_prevents_502():
    """Verify that tasks like 'Implement Change Management Strategies' or 'Lead Team Meetings'
    always reach the required minimum 2 tools and never crash with 502."""
    from app.services.task_ai_tools import _ensure_minimum_tools_for_prepared, _tasks_lacking_tools

    tasks = [
        {
            "task_id": "cm-1",
            "title": "Implement Change Management Strategies",
            "components": [{"name": "Stakeholder Engagement & Adoption"}],
        },
        {
            "task_id": "meet-1",
            "title": "Lead Team Meetings",
            "components": [{"name": "Meeting Agenda & Action Tracking"}],
        },
    ]

    incomplete_prepared = [
        {
            "task_id": "cm-1",
            "title": "Implement Change Management Strategies",
            "components": [
                {
                    "name": "Stakeholder Engagement & Adoption",
                    "tools": [
                        _tool(
                            "WalkMe",
                            access_class="enterprise",
                            why="WalkMe guides employees through system transformations and tracks digital adoption.",
                            how="Deploy WalkMe in-app walkthroughs for the change management rollout.",
                            connection="Digital adoption for change management strategies",
                        )
                    ],
                }
            ],
        },
        {
            "task_id": "meet-1",
            "title": "Lead Team Meetings",
            "components": [
                {
                    "name": "Meeting Agenda & Action Tracking",
                    "tools": [],
                }
            ],
        },
    ]

    missing_before = _tasks_lacking_tools(tasks, incomplete_prepared)
    # Task with 1 tool (Change Management) is valid; only task with 0 tools (Lead Team Meetings) is missing
    assert missing_before == ["Lead Team Meetings"]

    rescued = _ensure_minimum_tools_for_prepared(tasks, incomplete_prepared)
    missing_after = _tasks_lacking_tools(tasks, rescued)
    assert missing_after == []

    for p_task in rescued:
        for comp in p_task["components"]:
            assert len(comp["tools"]) >= 1
            for tool in comp["tools"]:
                assert tool["name"]
                assert len(tool["pros"]) >= 2
                assert len(tool["cons"]) >= 2
                assert tool["access_class"] in {"enterprise", "external"}

