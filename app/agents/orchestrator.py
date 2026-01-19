"""Orchestrator Agent - Coordinates the PDF generation workflow."""

import logging
from typing import Dict, Any

from app.agents.base import BaseAgent
from app.agents.state import AgentState, create_initial_state

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Agent for orchestrating the PDF generation workflow."""

    def __init__(self):
        super().__init__("Orchestrator")

    def process(self, state: AgentState) -> AgentState:
        """Initialize and validate the workflow.

        Args:
            state: Current agent state

        Returns:
            Updated state ready for processing
        """
        self.logger.info("Orchestrator initializing workflow...")

        # Check for basic input validity
        if not state.get('raw_input'):
            state['error'] = "No input data provided"
            return state

        raw_input = state['raw_input']

        # Validate input structure
        if not isinstance(raw_input, dict):
            state['error'] = "Input must be a JSON object"
            return state

        # Check for data section
        if 'data' not in raw_input:
            state['error'] = "Input must contain a 'data' field"
            return state

        if not isinstance(raw_input['data'], dict):
            state['error'] = "'data' field must be a JSON object"
            return state

        if not raw_input['data']:
            state['error'] = "'data' field cannot be empty"
            return state

        self.logger.info(
            f"Workflow initialized with {len(raw_input['data'])} sections"
        )

        return state

    def should_continue(self, state: AgentState) -> str:
        """Determine the next step in the workflow.

        Args:
            state: Current agent state

        Returns:
            Next node name or 'end'
        """
        if state.get('error'):
            return 'end'

        if not state.get('is_valid'):
            return 'end'

        return 'continue'


def orchestrate_pdf_generation(input_data: Dict[str, Any]) -> AgentState:
    """Entry point for PDF generation workflow.

    Args:
        input_data: Raw input JSON data

    Returns:
        Final agent state with results
    """
    # Create initial state
    state = create_initial_state(input_data)

    # Import here to avoid circular imports
    from app.agents.graph import run_workflow

    # Run the workflow
    final_state = run_workflow(state)

    return final_state


# Singleton instance
orchestrator_agent = OrchestratorAgent()
