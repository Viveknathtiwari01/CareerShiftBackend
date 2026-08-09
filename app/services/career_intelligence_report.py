import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PIPELINE_STATUS_COMPLETED
from app.models.career_intelligence_report import CareerIntelligenceReport
from app.repositories.assessment import assessment_repo
from app.repositories.assessment_task import assessment_task_repo
from app.repositories.assessment_task_analysis import assessment_task_analysis_repo
from app.repositories.career_intelligence_report import (
    CareerIntelligenceReportRepository,
    career_intelligence_report_repo,
)
from app.repositories.competency_mapping import competency_mapping_repo
from app.repositories.profile import profile_repo
from app.repositories.user import user_repo
from app.schemas.career_intelligence_report import CareerIntelligenceReportResponse
from app.services.report_generator import (
    REPORT_VERSION,
    ReportGeneratorInput,
    generate_career_intelligence_report,
    resolve_report_toolkit,
)
from app.services.report_export import (
    generate_scorecard,
    render_report_docx,
    render_report_pdf,
    render_toolkit_html,
)
from app.schemas.report_export import ReportScorecardResponse
from app.services.email import EmailService
from app.core.config import settings

logger = logging.getLogger(__name__)


def _next_report_version(existing: CareerIntelligenceReport | None) -> str:
    if not existing:
        return REPORT_VERSION
    current = existing.report_version or REPORT_VERSION
    if current.count(".") >= 1:
        major, minor = current.split(".", 1)
        try:
            return f"{major}.{int(minor) + 1}"
        except ValueError:
            pass
    return f"{current}.1"


def _profile_to_dict(profile) -> dict:
    return {
        "job_title": profile.job_title,
        "industry": profile.industry,
        "business_function": profile.business_function,
        "domain": profile.domain,
        "specialization": profile.specialization,
        "experience_years": profile.experience_years,
        "salary": profile.salary,
        "technical_skills": list(profile.technical_skills or []),
        "professional_skills": list(profile.professional_skills or []),
        "soft_skills": list(profile.soft_skills or []),
        "behavioural_skills": list(profile.behavioural_skills or []),
        "digital_skills": list(profile.digital_skills or []),
        "ai_frequency": profile.ai_frequency,
        "ai_tools": list(profile.ai_tools or []),
        "ai_comfort_level": profile.ai_comfort_level,
    }


def _task_routing_analyses(task_routing_json: dict | list | None) -> list[dict]:
    if isinstance(task_routing_json, dict):
        analyses = task_routing_json.get("analyses") or []
        return [dict(row) for row in analyses if isinstance(row, dict)]
    if isinstance(task_routing_json, list):
        return [dict(row) for row in task_routing_json if isinstance(row, dict)]
    return []


def _row_to_response(row: CareerIntelligenceReport) -> CareerIntelligenceReportResponse:
    supplemental = dict(row.supplemental_json or {})
    task_routing_analyses = _task_routing_analyses(row.task_routing_json)
    ai_toolkit = resolve_report_toolkit(row.ai_toolkit_json, task_routing_analyses)
    payload = {
        "assessment_id": row.assessment_id,
        "report_version": row.report_version,
        "generated_at": row.generated_at,
        "strategic_note": row.strategic_note,
        "overview": supplemental.get("overview"),
        "ai_readiness": row.ai_readiness_json,
        "task_routing": row.task_routing_json,
        "before_after": row.before_after_json,
        "upskill_roadmap": row.upskill_roadmap_json,
        "ai_toolkit": ai_toolkit,
        "cost_roi": row.cost_roi_json,
        "market_urgency": row.market_urgency_json,
        "action_plan": supplemental.get("action_plan"),
        "career_identity": supplemental.get("career_identity"),
        "competencies": supplemental.get("competencies"),
        "daily_work": supplemental.get("daily_work"),
    }
    return CareerIntelligenceReportResponse.model_validate(payload)


def _response_to_db_payload(response: CareerIntelligenceReportResponse) -> dict:
    return {
        "ai_readiness_json": response.ai_readiness.model_dump(mode="json"),
        "task_routing_json": response.task_routing.model_dump(mode="json"),
        "before_after_json": response.before_after.model_dump(mode="json"),
        "upskill_roadmap_json": [phase.model_dump(mode="json") for phase in response.upskill_roadmap],
        "ai_toolkit_json": {"tools": [item.model_dump(mode="json") for item in response.ai_toolkit]},
        "cost_roi_json": response.cost_roi.model_dump(mode="json"),
        "market_urgency_json": response.market_urgency.model_dump(mode="json"),
        "supplemental_json": {
            "overview": response.overview.model_dump(mode="json"),
            "competencies": [group.model_dump(mode="json") for group in response.competencies],
            "daily_work": response.daily_work.model_dump(mode="json"),
            "action_plan": response.action_plan.model_dump(mode="json"),
            "career_identity": response.career_identity.model_dump(mode="json"),
        },
        "strategic_note": response.strategic_note,
        "report_version": response.report_version,
        "generated_at": response.generated_at,
    }


class CareerIntelligenceReportService:
    def __init__(self, repository: CareerIntelligenceReportRepository | None = None) -> None:
        self._repo = repository or career_intelligence_report_repo

    async def _load_generator_input(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> ReportGeneratorInput:
        assessment = await assessment_repo.get_by_id_for_user(
            db, assessment_id=assessment_id, user_id=user_id
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        if assessment.status != PIPELINE_STATUS_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competency mapping must complete before generating a report.",
            )

        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        tasks = await assessment_task_repo.list_for_assessment(db, assessment_id=assessment_id)
        selected_tasks = [task for task in tasks if task.selected]
        if not selected_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one selected task is required to generate a report.",
            )

        analysis_rows = await assessment_task_analysis_repo.list_for_assessment(
            db, assessment_id=assessment_id
        )
        if len(analysis_rows) < len(selected_tasks):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Complete 3B analysis before generating the career intelligence report.",
            )

        mapping = await competency_mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
        competencies: list[dict] = []
        profession_summary = None
        if mapping and mapping.final_output_json:
            competencies = list(mapping.final_output_json.get("competencies") or [])
            profession_summary = mapping.final_output_json.get("profession_summary")

        analysis_by_task = {row.task_id: row for row in analysis_rows}
        task_payloads = []
        for task in selected_tasks:
            analysis = analysis_by_task.get(task.id)
            task_payloads.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "category": task.category,
                    "hours_per_week": task.hours_per_week,
                    "business_criticality": task.business_criticality,
                    "ai_assistance": task.ai_assistance,
                    "confidence_score": task.confidence_score or task.confidence,
                    "category_3b": analysis.category if analysis else None,
                }
            )

        analyses = [
            {
                "task_id": row.task_id,
                "task_title": row.task.title if row.task else "",
                "task_description": row.task.description if row.task else None,
                "task_category": row.task.category if row.task else None,
                "category": row.category,
                "rationale": row.rationale,
                "reason": row.reason,
                "next_actions": list(row.next_actions or []),
                "auto_potential": row.auto_potential,
                "risk_level": row.risk_level,
                "future_impact": row.future_impact,
                "recommended_tools": list(row.recommended_tools or []),
            }
            for row in analysis_rows
        ]

        return ReportGeneratorInput(
            assessment_id=assessment_id,
            profile=_profile_to_dict(profile),
            tasks=task_payloads,
            analyses=analyses,
            competencies=competencies,
            profession_summary=profession_summary,
        )

    async def get_report(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> CareerIntelligenceReportResponse:
        assessment = await assessment_repo.get_by_id_for_user(
            db, assessment_id=assessment_id, user_id=user_id
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

        row = await self._repo.get_by_assessment_id(db, assessment_id=assessment_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Career intelligence report has not been generated yet.",
            )
        return _row_to_response(row)

    async def generate_report(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        *,
        regenerate: bool = False,
    ) -> CareerIntelligenceReportResponse:
        existing = await self._repo.get_by_assessment_id(db, assessment_id=assessment_id)
        if existing and not regenerate:
            return _row_to_response(existing)

        generator_input = await self._load_generator_input(db, user_id, assessment_id)
        response = generate_career_intelligence_report(generator_input)
        response.report_version = _next_report_version(existing)
        payload = _response_to_db_payload(response)

        row = await self._repo.upsert(db, assessment_id=assessment_id, payload=payload)
        logger.info(
            "Career intelligence report generated for assessment %s version=%s",
            assessment_id,
            row.report_version,
        )
        result = _row_to_response(row)
        await self._notify_report_ready(db, user_id, result)
        return result

    async def _notify_report_ready(
        self,
        db: AsyncSession,
        user_id: UUID,
        report: CareerIntelligenceReportResponse,
    ) -> None:
        user = await user_repo.get(db, id=user_id)
        profile = await profile_repo.get_by_user_id(db, user_id)
        if not user or not profile:
            return

        recipient = user.first_name or user.username
        report_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/report?assessmentId={report.assessment_id}"
        try:
            await EmailService.send_report_ready_email(
                to_email=user.email,
                recipient_name=recipient,
                job_title=profile.job_title,
                score=report.ai_readiness.overall_score,
                tier_label=report.ai_readiness.tier_label,
                report_url=report_url,
            )
        except Exception:
            logger.exception("Failed to send report ready notification for user %s", user_id)

    async def get_scorecard(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> ReportScorecardResponse:
        report = await self.get_report(db, user_id, assessment_id)
        profile = await profile_repo.get_by_user_id(db, user_id)
        job_title = profile.job_title if profile else None
        return generate_scorecard(report, job_title=job_title)

    async def export_report_pdf(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        *,
        recipient_name: str,
    ) -> bytes:
        report = await self.get_report(db, user_id, assessment_id)
        profile = await profile_repo.get_by_user_id(db, user_id)
        job_title = profile.job_title if profile else report.before_after.role_today
        return render_report_pdf(report, recipient_name=recipient_name, job_title=job_title)

    async def export_report_docx(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        *,
        recipient_name: str,
    ) -> bytes:
        report = await self.get_report(db, user_id, assessment_id)
        profile = await profile_repo.get_by_user_id(db, user_id)
        job_title = profile.job_title if profile else report.before_after.role_today
        return render_report_docx(report, recipient_name=recipient_name, job_title=job_title)

    async def export_toolkit_html(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> str:
        report = await self.get_report(db, user_id, assessment_id)
        profile = await profile_repo.get_by_user_id(db, user_id)
        job_title = profile.job_title if profile else report.before_after.role_today
        return render_toolkit_html(report, job_title=job_title)


career_intelligence_report_service = CareerIntelligenceReportService()
