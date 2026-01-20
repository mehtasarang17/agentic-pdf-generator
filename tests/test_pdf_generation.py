"""Tests for PDF generation workflow."""

import pytest
import json
from unittest.mock import patch, MagicMock

from app import create_app
from app.agents.state import create_initial_state, AgentState
from app.agents.input_analyser import InputAnalyserAgent
from app.agents.planner import PlannerAgent
from app.agents.visualizer import VisualizerAgent
from app.services.chart_service import ChartService


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_input():
    """Sample input data for testing."""
    return {
        "client_name": "Test Corp",
        "data": {
            "executive_summary": {
                "type": "descriptive",
                "content": {
                    "overview": "Company security posture analysis",
                    "findings": ["Finding 1", "Finding 2"]
                }
            },
            "vulnerability_metrics": {
                "type": "analytics",
                "content": {
                    "critical": 5,
                    "high": 12,
                    "medium": 45,
                    "low": 89
                }
            }
        }
    }


@pytest.fixture
def analytics_only_input():
    """Analytics-only input data."""
    return {
        "client_name": "Analytics Corp",
        "data": {
            "metrics": {
                "type": "analytics",
                "content": {
                    "value_a": 100,
                    "value_b": 200,
                    "value_c": 150
                }
            }
        }
    }


class TestInputAnalyser:
    """Tests for Input Analyser Agent."""

    def test_valid_input_analysis(self, sample_input):
        """Test analysis of valid input."""
        state = create_initial_state(sample_input)
        agent = InputAnalyserAgent()

        result = agent.process(state)

        assert result['is_valid'] is True
        assert len(result['validation_errors']) == 0
        assert len(result['sections_identified']) == 2
        assert result['has_analytics'] is True
        assert result['has_descriptive'] is True

    def test_empty_input(self):
        """Test handling of empty input."""
        state = create_initial_state({})
        agent = InputAnalyserAgent()

        result = agent.process(state)

        assert result['is_valid'] is False
        assert len(result['validation_errors']) > 0

    def test_missing_data_section(self):
        """Test handling of input without data section."""
        state = create_initial_state({"client_name": "Test"})
        agent = InputAnalyserAgent()

        result = agent.process(state)

        assert result['is_valid'] is False
        assert "No 'data' section found" in result['validation_errors'][0]

    def test_infer_analytics_type(self, analytics_only_input):
        """Test type inference for analytics data."""
        state = create_initial_state(analytics_only_input)
        agent = InputAnalyserAgent()

        result = agent.process(state)

        assert result['is_valid'] is True
        assert result['has_analytics'] is True

    def test_unstructured_section_content(self):
        """Test handling of sections without type/content schema."""
        state = create_initial_state({
            "data": {
                "results": {
                    "status": "ok",
                    "count": 12,
                    "items": [{"id": 1}, {"id": 2}]
                }
            }
        })
        agent = InputAnalyserAgent()

        result = agent.process(state)

        assert result['is_valid'] is True
        assert result['sections_identified'][0]['content']['status'] == "ok"
        assert result['sections_identified'][0]['content']['count'] == 12


class TestChartService:
    """Tests for Chart Service."""

    def test_bar_chart_creation(self):
        """Test bar chart creation."""
        service = ChartService()
        data = {"A": 10, "B": 20, "C": 15}

        result = service.create_bar_chart(data, title="Test Bar Chart")

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_pie_chart_creation(self):
        """Test pie chart creation."""
        service = ChartService()
        data = {"Category 1": 30, "Category 2": 40, "Category 3": 30}

        result = service.create_pie_chart(data, title="Test Pie Chart")

        assert result is not None
        assert isinstance(result, bytes)

    def test_line_chart_creation(self):
        """Test line chart creation."""
        service = ChartService()
        data = {"Series 1": [1, 2, 3, 4, 5]}

        result = service.create_line_chart(data, title="Test Line Chart")

        assert result is not None
        assert isinstance(result, bytes)

    def test_radar_chart_creation(self):
        """Test radar chart creation."""
        service = ChartService()
        data = {"Metric 1": 80, "Metric 2": 70, "Metric 3": 90, "Metric 4": 60}

        result = service.create_radar_chart(data, title="Test Radar Chart")

        assert result is not None
        assert isinstance(result, bytes)


class TestAPIEndpoints:
    """Tests for API endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_generate_pdf_no_data(self, client):
        """Test PDF generation with no data."""
        response = client.post(
            '/api/v1/generate-pdf',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_generate_pdf_invalid_structure(self, client):
        """Test PDF generation with invalid structure."""
        response = client.post(
            '/api/v1/generate-pdf',
            data=json.dumps({"client_name": "Test"}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'

    def test_list_pdfs(self, client):
        """Test listing PDFs endpoint."""
        response = client.get('/api/v1/pdfs')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'pdfs' in data

    def test_download_invalid_pdf(self, client):
        """Test downloading non-existent PDF."""
        response = client.get('/api/v1/download/00000000-0000-0000-0000-000000000000')

        assert response.status_code == 404


class TestAgentState:
    """Tests for Agent State."""

    def test_initial_state_creation(self, sample_input):
        """Test initial state creation."""
        state = create_initial_state(sample_input)

        assert state['raw_input'] == sample_input
        assert state['client_name'] == "Test Corp"
        assert state['is_valid'] is False
        assert state['error'] is None

    def test_state_fields_exist(self, sample_input):
        """Test all required state fields exist."""
        state = create_initial_state(sample_input)

        required_fields = [
            'raw_input', 'client_name', 'is_valid', 'validation_errors',
            'sections_identified', 'has_analytics', 'has_descriptive',
            'pdf_title', 'section_plans', 'total_pages',
            'generated_descriptions', 'generated_bullets', 'generated_findings',
            'section_summaries', 'charts',
            'sections_content', 'pdf_result', 'error'
        ]

        for field in required_fields:
            assert field in state, f"Missing field: {field}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
