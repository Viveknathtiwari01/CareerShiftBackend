import pytest

from app.pipelines.context import CompetencyPipelineContext
from app.pipelines.stages import PipelineStage


SAMPLE_PROFILE = {
    "job_title": "Lead HRIS Analyst",
    "industry": "Professional & Business Services",
    "business_function": "Business Process Outsourcing",
    "domain": "Human Resources Process Outsourcing",
    "specialization": "HRIS Implementation & Management",
    "technical_skills": ["HRIS Implementation", "HR Data Management"],
    "experience_years": 5,
}

ROLE_OUTPUT = {
    "profession": "Human Resources Information Systems",
    "role_family": "HR Operations",
    "purpose": "Enable organizations to manage workforce data efficiently.",
    "functional_areas": ["HRIS Administration", "Data Management"],
}

DISCOVERY_OUTPUT = {
    "technical": ["HRIS Configuration"],
    "behavioural": ["Stakeholder Communication"],
    "leadership": [],
    "analytical": ["Workforce Analytics"],
}


class TestCompetencyPipelineContext:
    def test_role_understanding_input_from_profile(self):
        ctx = CompetencyPipelineContext(profile=SAMPLE_PROFILE)
        assert ctx.build_stage_input(PipelineStage.ROLE_UNDERSTANDING) == SAMPLE_PROFILE

    def test_discovery_input_from_role_understanding(self):
        ctx = CompetencyPipelineContext(profile=SAMPLE_PROFILE, role_understanding=ROLE_OUTPUT)
        assert ctx.build_stage_input(PipelineStage.COMPETENCY_DISCOVERY) == {
            "profession": ROLE_OUTPUT["profession"],
            "functional_areas": ROLE_OUTPUT["functional_areas"],
        }

    def test_structuring_input(self):
        ctx = CompetencyPipelineContext(
            profile=SAMPLE_PROFILE,
            role_understanding=ROLE_OUTPUT,
            competency_discovery=DISCOVERY_OUTPUT,
        )
        assert ctx.build_stage_input(PipelineStage.COMPETENCY_STRUCTURING) == {
            "profession": ROLE_OUTPUT["profession"],
            "role_family": ROLE_OUTPUT["role_family"],
            "purpose": ROLE_OUTPUT["purpose"],
            "competencies": DISCOVERY_OUTPUT,
        }

    def test_validation_input(self):
        structured = [{"name": "HRIS Configuration", "category": "Technical", "description": "..."}]
        ctx = CompetencyPipelineContext(
            profile=SAMPLE_PROFILE,
            role_understanding=ROLE_OUTPUT,
            competency_structuring=structured,
        )
        assert ctx.build_stage_input(PipelineStage.COMPETENCY_VALIDATION) == {
            "profession": ROLE_OUTPUT["profession"],
            "purpose": ROLE_OUTPUT["purpose"],
            "functional_areas": ROLE_OUTPUT["functional_areas"],
            "competencies": structured,
        }

    def test_explanation_input(self):
        validation = {"validated_competencies": [{"name": "HRIS Configuration"}]}
        ctx = CompetencyPipelineContext(
            profile=SAMPLE_PROFILE,
            role_understanding=ROLE_OUTPUT,
            competency_validation=validation,
        )
        assert ctx.build_stage_input(PipelineStage.COMPETENCY_EXPLANATION) == {
            "profession": ROLE_OUTPUT["profession"],
            "purpose": ROLE_OUTPUT["purpose"],
            "validated_competencies": validation["validated_competencies"],
        }

    def test_completed_stages(self):
        ctx = CompetencyPipelineContext(
            profile=SAMPLE_PROFILE,
            role_understanding=ROLE_OUTPUT,
            competency_discovery=DISCOVERY_OUTPUT,
        )
        completed = ctx.completed_stages()
        assert PipelineStage.ROLE_UNDERSTANDING in completed
        assert PipelineStage.COMPETENCY_DISCOVERY in completed
        assert PipelineStage.COMPETENCY_STRUCTURING not in completed
