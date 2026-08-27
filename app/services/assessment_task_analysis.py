import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PIPELINE_STATUS_COMPLETED
from app.models.assessment_task_analysis import AssessmentTaskAnalysis
from app.repositories.assessment import assessment_repo
from app.repositories.assessment_task import assessment_task_repo
from app.repositories.assessment_task_analysis import (
    AssessmentTaskAnalysisRepository,
    assessment_task_analysis_repo,
)
from app.repositories.competency_mapping import competency_mapping_repo
from app.repositories.profile import profile_repo
from app.schemas.assessment_task_analysis import (
    HoursBucket,
    HoursByCategory,
    HoursSummary,
    TaskAnalysisItem,
    TaskAnalysisRunResponse,
)
from app.services.report_generator import analysis_dicts_from_rows, build_toolkit_from_analyses
from app.services.task_3b_classification import classify_tasks_3b_from_ai
from app.services.task_3b_grounding import build_3b_grounding_payload
from app.services.task_analysis_input_hash import compute_task_analysis_input_hash
from app.services.task_hours import annual_hours_from_weekly, compute_hours_summary, effective_task_hours

logger = logging.getLogger(__name__)


class AssessmentTaskAnalysisService:
    def __init__(
        self,
        repository: AssessmentTaskAnalysisRepository | None = None,
    ) -> None:
        self._repo = repository or assessment_task_analysis_repo

    async def _get_owned_assessment(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ):
        assessment = await assessment_repo.get_by_id_for_user(
            db, assessment_id=assessment_id, user_id=user_id
        )
        if not assessment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")
        return assessment

    def _hours_response_parts(
        self,
        rows: list[AssessmentTaskAnalysis],
    ) -> tuple[HoursByCategory, HoursSummary, float]:
        pairs = [(row.task, row.category) for row in rows if row.task]
        summary_dict = compute_hours_summary(pairs)
        hours_summary = HoursSummary(
            BUILD=HoursBucket(**summary_dict["BUILD"]),
            BLEND=HoursBucket(**summary_dict["BLEND"]),
            BOT=HoursBucket(**summary_dict["BOT"]),
            total=HoursBucket(**summary_dict["total"]),
        )
        hours_by_category = HoursByCategory(
            BUILD=hours_summary.BUILD.weekly_hours,
            BLEND=hours_summary.BLEND.weekly_hours,
            BOT=hours_summary.BOT.weekly_hours,
        )
        return hours_by_category, hours_summary, hours_summary.total.weekly_hours

    def _to_item(self, row: AssessmentTaskAnalysis) -> TaskAnalysisItem:
        task = row.task
        weekly = effective_task_hours(task) if task else 0.0
        return TaskAnalysisItem(
            task_id=row.task_id,
            task_title=task.title if task else "",
            task_description=task.description if task else None,
            task_category=task.category if task else None,
            category=row.category,
            rationale=row.rationale,
            reason=row.reason,
            next_actions=list(row.next_actions or [])[:3],
            auto_potential=row.auto_potential,
            risk_level=row.risk_level,
            future_impact=row.future_impact,
            recommended_tools=list(row.recommended_tools or []),
            components=list(row.components or []),
            weekly_hours=round(weekly, 1),
            annual_hours=annual_hours_from_weekly(weekly),
            importance=row.importance,
            feasibility_tier=row.feasibility_tier,
            feasibility_note=row.feasibility_note,
            human_capability=row.human_capability,
            velocity=row.velocity,
            velocity_note=row.velocity_note,
            next_action=row.next_action,
            learn_gap=row.learn_gap,
            learn_do=row.learn_do,
            learn_dont=row.learn_dont,
            where_to_learn=row.where_to_learn,
            status=row.status,
        )

    @staticmethod
    def _task_title_for_row(row: AssessmentTaskAnalysis) -> str:
        return row.task.title if row.task else ""

    async def _persist_toolkit_snapshot(
        self,
        db: AsyncSession,
        assessment,
        analyses: list[dict],
    ) -> None:
        assessment.ai_toolkit_json = {"tools": build_toolkit_from_analyses(analyses)}
        db.add(assessment)
        await db.flush()

    def _build_response(
        self,
        rows: list[AssessmentTaskAnalysis],
        *,
        summary_confidence: int | None,
        regenerated: bool,
        market_reality: dict | None = None,
        generated_at: datetime | None = None,
    ) -> TaskAnalysisRunResponse:
        hours_cat, hours_summary, total = self._hours_response_parts(rows)
        return TaskAnalysisRunResponse(
            analyses=[self._to_item(r) for r in rows],
            summary_confidence=summary_confidence,
            regenerated=regenerated,
            hours_by_category=hours_cat,
            hours_summary=hours_summary,
            total_hours=total,
            generated_at=generated_at,
            market_reality=market_reality,
        )

    async def get_analysis(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
    ) -> TaskAnalysisRunResponse:
        assessment = await self._get_owned_assessment(db, user_id, assessment_id)
        rows = await self._repo.list_for_assessment(db, assessment_id=assessment_id)
        summary = self._average_confidence(rows)
        generated_at = assessment.task_analysis_generated_at
        if not generated_at and rows:
            generated_at = max((r.created_at for r in rows), default=None)
        return self._build_response(
            rows,
            summary_confidence=summary,
            regenerated=False,
            market_reality=assessment.market_reality_json,
            generated_at=generated_at,
        )

    async def analyze_tasks(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        *,
        regenerate: bool = False,
    ) -> TaskAnalysisRunResponse:
        assessment = await self._get_owned_assessment(db, user_id, assessment_id)

        if assessment.status != PIPELINE_STATUS_COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competency mapping must complete before 3B analysis.",
            )

        all_tasks = await assessment_task_repo.list_for_assessment(db, assessment_id=assessment_id)
        selected_tasks = [t for t in all_tasks if t.selected]
        if len(selected_tasks) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one selected task is required for 3B analysis.",
            )

        existing = await self._repo.list_for_assessment(db, assessment_id=assessment_id)
        profile = await profile_repo.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

        mapping = await competency_mapping_repo.get_by_assessment_id(db, assessment_id=assessment_id)
        final_output = mapping.final_output_json if mapping else None
        current_input_hash = compute_task_analysis_input_hash(final_output, selected_tasks)
        stored_hash = assessment.task_analysis_input_hash

        if existing and stored_hash and stored_hash == current_input_hash:
            if not (assessment.ai_toolkit_json or {}).get("tools"):
                analyses_payload = analysis_dicts_from_rows(
                    existing,
                    task_title_for=self._task_title_for_row,
                )
                await self._persist_toolkit_snapshot(db, assessment, analyses_payload)
                await db.commit()
            summary = self._average_confidence(existing)
            logger.info(
                "Returning locked 3B analysis for assessment %s (regenerate=%s ignored)",
                assessment_id,
                regenerate,
            )
            return self._build_response(
                existing,
                summary_confidence=summary,
                regenerated=False,
                market_reality=assessment.market_reality_json,
                generated_at=assessment.task_analysis_generated_at
                or max((r.created_at for r in existing), default=None),
            )

        if existing and stored_hash and stored_hash != current_input_hash:
            logger.info("3B inputs changed for assessment %s — regenerating", assessment_id)
            await self._repo.delete_for_assessment(db, assessment_id=assessment_id)
            existing = []

        if existing and not stored_hash:
            if not (assessment.ai_toolkit_json or {}).get("tools"):
                analyses_payload = analysis_dicts_from_rows(
                    existing,
                    task_title_for=self._task_title_for_row,
                )
                await self._persist_toolkit_snapshot(db, assessment, analyses_payload)
                await db.commit()
            summary = self._average_confidence(existing)
            assessment.task_analysis_input_hash = current_input_hash
            assessment.task_analysis_generated_at = max(
                (r.created_at for r in existing), default=datetime.now(timezone.utc)
            )
            db.add(assessment)
            await db.commit()
            return self._build_response(
                existing,
                summary_confidence=summary,
                regenerated=False,
                market_reality=assessment.market_reality_json,
                generated_at=assessment.task_analysis_generated_at,
            )

        grounding_payload = build_3b_grounding_payload(
            profile,
            final_output,
            selected_tasks,
        )

        ai_result = await classify_tasks_3b_from_ai(grounding_payload=grounding_payload)
        analyses_by_index = {item["task_index"]: item for item in ai_result.get("analyses", [])}

        await self._repo.delete_for_assessment(db, assessment_id=assessment_id)

        new_rows: list[AssessmentTaskAnalysis] = []
        for idx, task in enumerate(selected_tasks):
            item = analyses_by_index.get(idx)
            if not item:
                logger.error("Missing 3B analysis for task index %d (task_id=%s)", idx, task.id)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "AI analysis did not return results for all tasks. "
                        "Please retry the analysis."
                    ),
                )

            new_rows.append(
                AssessmentTaskAnalysis(
                    task_id=task.id,
                    category=item["category"],
                    rationale=item.get("rationale"),
                    reason=item.get("reason"),
                    next_actions=item.get("next_actions") or [],
                    auto_potential=item.get("auto_potential"),
                    risk_level=item.get("risk_level"),
                    future_impact=item.get("future_impact"),
                    recommended_tools=item.get("recommended_tools") or [],
                    components=item.get("components") or [],
                    importance=item.get("importance"),
                    feasibility_tier=item.get("feasibility_tier"),
                    feasibility_note=item.get("feasibility_note"),
                    human_capability=item.get("human_capability"),
                    velocity=item.get("velocity"),
                    velocity_note=item.get("velocity_note"),
                    next_action=item.get("next_action"),
                    learn_gap=item.get("learn_gap"),
                    learn_do=item.get("learn_do"),
                    learn_dont=item.get("learn_dont"),
                    where_to_learn=item.get("where_to_learn"),
                )
            )

        created = await self._repo.bulk_create(db, rows=new_rows)
        for row, task in zip(created, selected_tasks):
            row.task = task

        analyses_payload = [
            {
                "task_id": str(row.task_id),
                "task_title": task.title,
                "category": row.category,
                "rationale": row.rationale,
                "reason": row.reason,
                "future_impact": row.future_impact,
                "auto_potential": row.auto_potential,
                "risk_level": row.risk_level,
                "recommended_tools": list(row.recommended_tools or []),
                "components": list(row.components or []),
            }
            for row, task in zip(created, selected_tasks)
        ]
        await self._persist_toolkit_snapshot(db, assessment, analyses_payload)
        generated_at = datetime.now(timezone.utc)
        assessment.task_analysis_input_hash = current_input_hash
        assessment.task_analysis_generated_at = generated_at
        assessment.market_reality_json = ai_result.get("market_reality") or {}
        db.add(assessment)
        await db.commit()

        logger.info("3B analysis saved for assessment %s (%d tasks)", assessment_id, len(created))

        return self._build_response(
            created,
            summary_confidence=ai_result.get("summary_confidence"),
            regenerated=bool(existing),
            market_reality=ai_result.get("market_reality"),
            generated_at=generated_at,
        )

    async def update_task_status(
        self,
        db: AsyncSession,
        user_id: UUID,
        assessment_id: UUID,
        task_id: UUID,
        status_val: str | None,
    ) -> TaskAnalysisItem:
        await self._get_owned_assessment(db, user_id, assessment_id)
        row = await self._repo.get_by_task_id(db, task_id=task_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found for task.")
        row.status = status_val
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return self._to_item(row)

    @staticmethod
    def _average_confidence(rows: list[AssessmentTaskAnalysis]) -> int | None:
        potentials = [r.auto_potential for r in rows if r.auto_potential is not None]
        if not potentials:
            return None
        return round(sum(potentials) / len(potentials))


assessment_task_analysis_service = AssessmentTaskAnalysisService()
