from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit_report_generate
from app.models.user import User
from app.schemas.career_intelligence_report import CareerIntelligenceReportResponse
from app.schemas.common import APIResponse
from app.schemas.report_export import ReportScorecardResponse
from app.services.career_intelligence_report import (
    CareerIntelligenceReportService,
    career_intelligence_report_service,
)

router = APIRouter()


def get_report_service() -> CareerIntelligenceReportService:
    return career_intelligence_report_service


def _attachment(filename: str, content_type: str) -> dict[str, str]:
    return {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": content_type,
    }


@router.get("/{assessment_id}/report", response_model=APIResponse[CareerIntelligenceReportResponse])
async def get_career_report(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    report_service: CareerIntelligenceReportService = Depends(get_report_service),
):
    data = await report_service.get_report(db, current_user.id, assessment_id)
    return APIResponse(success=True, message="Career intelligence report retrieved", data=data)


@router.post(
    "/{assessment_id}/generate-report",
    response_model=APIResponse[CareerIntelligenceReportResponse],
)
async def generate_career_report(
    assessment_id: UUID,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(rate_limit_report_generate),
    db: AsyncSession = Depends(get_db),
    report_service: CareerIntelligenceReportService = Depends(get_report_service),
):
    data = await report_service.generate_report(
        db, current_user.id, assessment_id, regenerate=regenerate
    )
    return APIResponse(success=True, message="Career intelligence report generated", data=data)


@router.get("/{assessment_id}/readiness", response_model=APIResponse[dict])
async def get_assessment_readiness(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    report_service: CareerIntelligenceReportService = Depends(get_report_service),
):
    report = await report_service.get_report(db, current_user.id, assessment_id)
    return APIResponse(
        success=True,
        message="AI readiness retrieved",
        data=report.ai_readiness.model_dump(),
    )


@router.get("/{assessment_id}/report/pdf")
async def download_report_pdf(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    report_service: CareerIntelligenceReportService = Depends(get_report_service),
):
    pdf_bytes = await report_service.get_report_pdf(
        db, current_user.id, assessment_id, current_user
    )
    filename = "careershift-report.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers=_attachment(filename, "application/pdf"),
    )


@router.get("/{assessment_id}/report/toolkit")
async def download_toolkit_html(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    report_service: CareerIntelligenceReportService = Depends(get_report_service),
):
    html = await report_service.get_toolkit_html(
        db, current_user.id, assessment_id, current_user
    )
    filename = f"careershift-toolkit-{assessment_id}.html"
    return Response(content=html, media_type="text/html", headers=_attachment(filename, "text/html"))


@router.get("/{assessment_id}/report/scorecard", response_model=APIResponse[ReportScorecardResponse])
async def get_report_scorecard(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    report_service: CareerIntelligenceReportService = Depends(get_report_service),
):
    data = await report_service.get_scorecard(
        db, current_user.id, assessment_id, current_user
    )
    return APIResponse(success=True, message="Scorecard generated", data=data)


@router.get("/{assessment_id}/report/export.json")
async def download_report_json(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    report_service: CareerIntelligenceReportService = Depends(get_report_service),
):
    payload = await report_service.get_export_json(db, current_user.id, assessment_id)
    import json

    content = json.dumps(payload, indent=2, default=str)
    filename = "careershift-report.json"
    return Response(
        content=content,
        media_type="application/json",
        headers=_attachment(filename, "application/json"),
    )
