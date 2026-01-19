"""Input Analyser Agent - Validates and analyzes JSON input."""

import logging
from typing import Dict, Any, List

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.config import config

logger = logging.getLogger(__name__)


class InputAnalyserAgent(BaseAgent):
    """Agent for validating and analyzing input JSON data."""

    def __init__(self):
        super().__init__("InputAnalyser")

    def process(self, state: AgentState) -> AgentState:
        """Validate and analyze the input data.

        Args:
            state: Current agent state with raw_input

        Returns:
            Updated state with validation results and identified sections
        """
        raw_input = state['raw_input']
        validation_errors = []
        sections_identified = []
        has_analytics = False
        has_descriptive = False

        # Check if data exists
        if not raw_input:
            validation_errors.append("Input data is empty")
            state['is_valid'] = False
            state['validation_errors'] = validation_errors
            return state

        # Extract data section
        data = raw_input.get('data', {})
        if not data:
            validation_errors.append("No 'data' section found in input")
            state['is_valid'] = False
            state['validation_errors'] = validation_errors
            return state

        # Analyze each section
        for section_name, section_data in data.items():
            if not isinstance(section_data, dict):
                validation_errors.append(
                    f"Section '{section_name}' must be a dictionary"
                )
                continue

            section_type = section_data.get('type', 'descriptive')
            content = section_data.get('content', {})

            # Determine type if not specified
            if section_type not in ['analytics', 'descriptive']:
                section_type = self._infer_section_type(content)

            # Track section types
            if section_type == 'analytics':
                has_analytics = True
            else:
                has_descriptive = True

            sections_identified.append({
                'name': self._format_section_name(section_name),
                'original_name': section_name,
                'type': section_type,
                'content': content
            })

        # Validate minimum content
        if not sections_identified:
            validation_errors.append("No valid sections found in data")

        # Update state
        state['is_valid'] = len(validation_errors) == 0
        state['validation_errors'] = validation_errors
        state['sections_identified'] = sections_identified
        state['has_analytics'] = has_analytics
        state['has_descriptive'] = has_descriptive
        state['client_name'] = raw_input.get('client_name')

        self.logger.info(
            f"Analyzed input: {len(sections_identified)} sections, "
            f"analytics={has_analytics}, descriptive={has_descriptive}"
        )

        return state

    def _infer_section_type(self, content: Dict[str, Any]) -> str:
        """Infer section type from content structure.

        Args:
            content: Section content dictionary

        Returns:
            'analytics' or 'descriptive'
        """
        if not content:
            return 'descriptive'

        # Check if content has primarily numeric values
        numeric_count = 0
        total_count = 0

        for key, value in content.items():
            total_count += 1
            if isinstance(value, (int, float)):
                numeric_count += 1
            elif isinstance(value, dict):
                # Recursively check nested dicts
                for v in value.values():
                    if isinstance(v, (int, float)):
                        numeric_count += 1
                    total_count += 1

        # If more than 50% of values are numeric, treat as analytics
        if total_count > 0 and numeric_count / total_count > 0.5:
            return 'analytics'

        return 'descriptive'

    def _format_section_name(self, name: str) -> str:
        """Format section name for display.

        Args:
            name: Raw section name

        Returns:
            Formatted section name
        """
        # Replace underscores with spaces and title case
        return name.replace('_', ' ').title()


# Singleton instance
input_analyser_agent = InputAnalyserAgent()
