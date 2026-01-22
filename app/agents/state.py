"""Agent state definition for LangGraph workflow."""

from typing import TypedDict, Optional, List, Dict, Any


class SectionPlan(TypedDict):
    """Plan for a single section."""
    name: str
    type: str  # 'analytics' or 'descriptive'
    content: Dict[str, Any]
    page_start: int
    needs_chart: bool
    chart_type: Optional[str]


class AgentState(TypedDict):
    """State passed between agents in the LangGraph workflow."""

    # Input data
    raw_input: Dict[str, Any]
    client_name: Optional[str]

    # Analysis results
    is_valid: bool
    validation_errors: List[str]
    sections_identified: List[Dict[str, Any]]
    has_analytics: bool
    has_descriptive: bool

    # Planning results
    pdf_title: str
    section_plans: List[SectionPlan]
    total_pages: int

    # Writer results
    generated_descriptions: Dict[str, str]
    generated_bullets: Dict[str, List[str]]
    generated_findings: Dict[str, List[str]]
    section_summaries: Dict[str, str]
    section_parts: Dict[str, List[Dict[str, Any]]]
    table_value_summaries: Dict[str, Dict[str, str]]

    # Visualizer results
    charts: Dict[str, List[bytes]]  # section_name -> list of chart images

    # Content builder results
    sections_content: List[Dict[str, Any]]

    # Final output
    pdf_result: Optional[Dict[str, Any]]
    error: Optional[str]


def create_initial_state(input_data: Dict[str, Any]) -> AgentState:
    """Create initial state from input data."""
    return AgentState(
        raw_input=input_data,
        client_name=input_data.get('client_name'),
        is_valid=False,
        validation_errors=[],
        sections_identified=[],
        has_analytics=False,
        has_descriptive=False,
        pdf_title="",
        section_plans=[],
        total_pages=0,
        generated_descriptions={},
        generated_bullets={},
        generated_findings={},
        section_summaries={},
        section_parts={},
        table_value_summaries={},
        charts={},
        sections_content=[],
        pdf_result=None,
        error=None
    )
