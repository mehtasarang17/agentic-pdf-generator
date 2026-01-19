"""LangGraph workflow for PDF generation."""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.orchestrator import orchestrator_agent
from app.agents.input_analyser import input_analyser_agent
from app.agents.planner import planner_agent
from app.agents.writer import writer_agent
from app.agents.visualizer import visualizer_agent
from app.agents.content_builder import content_builder_agent

logger = logging.getLogger(__name__)


def should_continue_after_orchestrator(state: AgentState) -> Literal["input_analyser", "end"]:
    """Determine if workflow should continue after orchestrator.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.get('error'):
        logger.warning(f"Workflow stopping due to error: {state['error']}")
        return "end"
    return "input_analyser"


def should_continue_after_analysis(state: AgentState) -> Literal["planner", "end"]:
    """Determine if workflow should continue after input analysis.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.get('error') or not state.get('is_valid'):
        logger.warning(f"Workflow stopping: valid={state.get('is_valid')}, errors={state.get('validation_errors')}")
        return "end"
    return "planner"


def determine_content_processing(state: AgentState) -> Literal["writer_only", "visualizer_only", "both", "content_builder"]:
    """Determine which content processing agents to run.

    Args:
        state: Current agent state

    Returns:
        Processing path
    """
    if state.get('error'):
        return "content_builder"

    has_analytics = state.get('has_analytics', False)
    has_descriptive = state.get('has_descriptive', False)

    if has_analytics and has_descriptive:
        return "both"
    elif has_analytics:
        return "visualizer_only"
    elif has_descriptive:
        return "writer_only"
    else:
        return "content_builder"


def should_continue_after_writer(state: AgentState) -> Literal["visualizer", "content_builder"]:
    """Determine next step after writer agent.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    if state.get('has_analytics'):
        return "visualizer"
    return "content_builder"


def create_pdf_workflow() -> StateGraph:
    """Create the LangGraph workflow for PDF generation.

    Returns:
        Compiled StateGraph
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_agent)
    workflow.add_node("input_analyser", input_analyser_agent)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("writer", writer_agent)
    workflow.add_node("visualizer", visualizer_agent)
    workflow.add_node("content_builder", content_builder_agent)

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Add conditional edges from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        should_continue_after_orchestrator,
        {
            "input_analyser": "input_analyser",
            "end": END
        }
    )

    # Add conditional edges from input analyser
    workflow.add_conditional_edges(
        "input_analyser",
        should_continue_after_analysis,
        {
            "planner": "planner",
            "end": END
        }
    )

    # Add conditional edges from planner based on data types
    workflow.add_conditional_edges(
        "planner",
        determine_content_processing,
        {
            "writer_only": "writer",
            "visualizer_only": "visualizer",
            "both": "writer",
            "content_builder": "content_builder"
        }
    )

    # Add conditional edges from writer
    workflow.add_conditional_edges(
        "writer",
        should_continue_after_writer,
        {
            "visualizer": "visualizer",
            "content_builder": "content_builder"
        }
    )

    # Visualizer always goes to content builder
    workflow.add_edge("visualizer", "content_builder")

    # Content builder goes to end
    workflow.add_edge("content_builder", END)

    return workflow.compile()


# Create compiled workflow
pdf_workflow = create_pdf_workflow()


def run_workflow(initial_state: AgentState) -> AgentState:
    """Run the PDF generation workflow.

    Args:
        initial_state: Initial agent state with input data

    Returns:
        Final agent state with results
    """
    logger.info("Starting PDF generation workflow...")

    try:
        # Run the workflow
        final_state = pdf_workflow.invoke(initial_state)
        logger.info("Workflow completed successfully")
        return final_state
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        initial_state['error'] = f"Workflow failed: {str(e)}"
        return initial_state
