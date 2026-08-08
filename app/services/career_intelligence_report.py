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
from app.schemas.career_intelligence_report import CareerIntelligenceReportResponse
from app.schemas.report_export import ReportScorecardResponse
from app.services.report_generator import (
    ReportGeneratorInput,
    build_toolkit_from_analyses,
    enrich_ai_toolkit,
    ensure_toolkit_priorities,
    generate_career_intelligence_report,
    needs_legacy_toolkit_enrichment,
    needs_toolkit_priority_backfill,
)
from app.services.report_export import (
    export_report_json,
    generate_scorecard,
    render_report_pdf,
    render_toolkit_html,
)
from app.core.config import settings
from app.services.email import EmailService
from app.repositories.user import user_repo

logger = logging.getLogger(__name__)


def _profile_to_dict(profile) -> dict:
    return {
        "job_title": profile.job_title,
        "industry": profile.industry,
        "business_function": profile.business_function,
        "domain": profile.domain,
        "specialization": profile.specialization,
        "experience_years": profile.experience_years,
        "ai_frequency": profile.ai_frequency,
        "ai_tools": profile.ai_tools or [],
        "ai_comfort_level": profile.ai_comfort_level,
    }


def _task_to_dict(task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "hours_per_week": task.hours_per_week,
        "complexity": task.complexity,
        "ai_assistance": task.ai_assistance,
        "selected": task.selected,
    }


def _analysis_to_dict(row, item) -> dict:
    return {
        "task_id": str(row.task_id),
        "task_title": item.task_title,
        "category": item.category,
        "rationale": item.rationale,
        "reason": item.reason,
        "next_actions": item.next_actions,
        "auto_potential": item.auto_potential,
        "risk_level": item.risk_level,
        "future_impact": item.future_impact,
        "recommended_tools": item.recommended_tools,
    }


def _row_to_response(row: CareerIntelligenceReport, payload: dict) -> CareerIntelligenceReportResponse:
    payload["assessment_id"] = row.assessment_id
    payload["report_version"] = row.report_version
    payload["generated_at"] = row.generated_at
    payload["strategic_note"] = row.strategic_note
    return CareerIntelligenceReportResponse.model_validate(payload)


class CareerIntelligenceReportService:
    def __init__(self, repository: CareerIntelligenceReportRepository | None = None) -> None:
        self._repo = repository or career_intelligence_report_repo

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
                detail="Report not generated yet. Submit your assessment first.",
            )

        payload = self._payload_from_row(row)
        return _row_to_response(row, payload)

    async def generate_report(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        *,
        regenerate: bool = False,
    ) -> CareerIntelligenceReportResponse:
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

        existing = await self._repo.get_by_assessment_id(db, assessment_id=assessment_id)
        if existing and not regenerate:
            payload = self._payload_from_row(existing)
            return _row_to_response(existing, payload)

        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        mapping = await competency_mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
        if not mapping or not mapping.final_output_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competency mapping output is missing.",
            )

        tasks = await assessment_task_repo.list_for_assessment(db, assessment_id=assessment_id)
        selected = [t for t in tasks if t.selected]
        if not selected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one selected task is required.",
            )

        from app.services.assessment_task_analysis import assessment_task_analysis_service

        analysis_rows = await assessment_task_analysis_repo.list_for_assessment(
            db, assessment_id=assessment_id
        )
        if len(analysis_rows) != len(selected):
            await assessment_task_analysis_service.analyze_tasks(
                db, user_id, assessment_id, regenerate=False
            )
            analysis_rows = await assessment_task_analysis_repo.list_for_assessment(
                db, assessment_id=assessment_id
            )

        if len(analysis_rows) < len(selected):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="3B analysis must complete before generating a report.",
            )

        await db.refresh(assessment)

        competencies = mapping.final_output_json.get("competencies") or []
        profession_summary = mapping.final_output_json.get("profession_summary")

        analyses = []
        for row in analysis_rows:
            item = assessment_task_analysis_service._to_item(row)
            analyses.append(_analysis_to_dict(row, item))

        stored_toolkit = (assessment.ai_toolkit_json or {}).get("tools")
        if not stored_toolkit:
            stored_toolkit = build_toolkit_from_analyses(analyses)
            assessment.ai_toolkit_json = {"tools": stored_toolkit}
            db.add(assessment)
            await db.flush()

        generated = generate_career_intelligence_report(
            ReportGeneratorInput(
                assessment_id=assessment_id,
                profile=_profile_to_dict(profile),
                profession_summary=profession_summary,
                competencies=competencies,
                tasks=[_task_to_dict(t) for t in selected],
                analyses=analyses,
                toolkit=stored_toolkit,
            )
        )

        persist = generated.pop("_persist")
        row = await self._repo.upsert(db, assessment_id=assessment_id, payload=persist)
        await db.commit()
        await db.refresh(row)

        logger.info("Generated career intelligence report for assessment %s", assessment_id)
        result = _row_to_response(row, generated)
        await self._notify_report_ready(db, user_id, result)
        return result

    async def _notify_report_ready(
        self,
        db: AsyncSession,
        user_id: UUID,
        report: CareerIntelligenceReportResponse,
    ) -> None:
        if not settings.REPORT_READY_EMAIL_ENABLED:
            return
        user = await user_repo.get(db, id=user_id)
        if not user:
            return
        recipient = user.first_name or user.username
        report_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/report?assessmentId={report.assessment_id}"
        try:
            await EmailService.send_report_ready_email(
                to_email=user.email,
                recipient_name=recipient,
                job_title=report.overview.job_title,
                score=report.ai_readiness.overall_score,
                tier_label=report.ai_readiness.tier_label,
                report_url=report_url,
            )
        except Exception:
            logger.exception("Failed to send report ready email for user %s", user_id)

    @staticmethod
    def display_name(user) -> str:
        if user.first_name:
            return f"{user.first_name} {user.last_name or ''}".strip()
        return user.username

    async def get_report_pdf(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        user,
    ) -> bytes:
        report = await self.get_report(db, user_id, assessment_id)
        return render_report_pdf(report, recipient_name=self.display_name(user))

    async def get_toolkit_html(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        user,
    ) -> str:
        report = await self.get_report(db, user_id, assessment_id)
        return render_toolkit_html(report, recipient_name=self.display_name(user))

    async def get_scorecard(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        user,
    ) -> ReportScorecardResponse:
        report = await self.get_report(db, user_id, assessment_id)
        return generate_scorecard(report, recipient_name=self.display_name(user))

    async def get_export_json(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> dict:
        report = await self.get_report(db, user_id, assessment_id)
        return export_report_json(report)

    @staticmethod
    def _payload_from_row(row: CareerIntelligenceReport) -> dict:
        overview = row.overview_json or {}
        task_routing = row.task_routing_json.get("items", [])
        ai_toolkit = row.ai_toolkit_json.get("tools", [])
        if needs_legacy_toolkit_enrichment(ai_toolkit):
            ai_toolkit = enrich_ai_toolkit(ai_toolkit, task_routing)
        if needs_toolkit_priority_backfill(ai_toolkit):
            ai_toolkit = ensure_toolkit_priorities(ai_toolkit, task_routing)
        return {
            "overview": overview,
            "ai_readiness": row.ai_readiness_json,
            "competencies": overview.get("competency_groups", []),
            "daily_work": {
                "tasks": row.task_routing_json.get("daily_tasks", []),
                "total_hours_per_week": overview.get("total_hours_per_week", 40),
            },
            "task_routing": task_routing,
            "career_identity": row.career_identity_json,
            "learning_roadmap": row.upskill_roadmap_json.get("phases", []),
            "ai_toolkit": ai_toolkit,
            "action_plan": row.action_plan_json,
            "before_after": row.before_after_json,
            "cost_roi": row.cost_roi_json,
            "market_urgency": row.market_urgency_json,
        }


career_intelligence_report_service = CareerIntelligenceReportService()
