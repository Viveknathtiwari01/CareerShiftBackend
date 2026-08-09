"""Integration-style smoke tests for production remediation endpoints."""

import pytest

from app.api.v1.assessment import analysis_routes, readiness_routes, report_routes
from app.api.v1.master import routes as master_routes


def test_submit_flow_endpoints_exist():
    analysis_paths = {route.path for route in analysis_routes.router.routes}
    report_paths = {route.path for route in report_routes.router.routes}
    readiness_paths = {route.path for route in readiness_routes.router.routes}

    assert "/{assessment_id}/analyze" in analysis_paths
    assert "/{assessment_id}/generate-report" in report_paths
    assert "/{assessment_id}/report" in report_paths
    assert "/{assessment_id}/readiness" in readiness_paths
    assert "/{assessment_id}/report/pdf" in report_paths
    assert "/{assessment_id}/report/toolkit" in report_paths
    assert "/{assessment_id}/report/scorecard" in report_paths


def test_master_profile_options_endpoint_exists():
    paths = {route.path for route in master_routes.router.routes}
    assert "/profile-options" in paths


def test_celery_task_is_registered_when_available():
    try:
        from app.tasks.pipeline import run_competency_pipeline_task

        assert run_competency_pipeline_task.name == "careershift.run_competency_pipeline"
    except ImportError:
        pytest.skip("Celery not installed")
