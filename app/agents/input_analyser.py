"""Input Analyser Agent - Validates and analyzes JSON input."""

import logging
from typing import Dict, Any, List, Tuple, Optional

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
            if isinstance(section_data, dict) and 'content' in section_data:
                section_type = section_data.get('type', 'descriptive')
                content = self._normalize_content(section_data.get('content', {}))
            else:
                content = self._normalize_content(section_data)
                section_type = self._infer_section_type(content)

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

        numeric_count, total_count = self._count_numeric_values(
            content,
            config.ANALYTICS_SAMPLE_LIMIT
        )
        has_series = self._has_numeric_series(
            content,
            config.ANALYTICS_SERIES_MIN_LENGTH
        )

        if has_series:
            return 'analytics'

        if total_count > 0 and numeric_count >= config.ANALYTICS_MIN_NUMERIC_VALUES:
            ratio = numeric_count / total_count
            if ratio >= config.ANALYTICS_NUMERIC_RATIO:
                return 'analytics'

        if numeric_count >= config.ANALYTICS_MIN_NUMERIC_VALUES * 2:
            return 'analytics'

        return 'descriptive'

    def _count_numeric_values(self, value: Any, sample_limit: int) -> Tuple[int, int]:
        """Count numeric vs total values with a sample cap."""
        numeric_count = 0
        total_count = 0
        stack = [value]

        while stack:
            if total_count >= sample_limit:
                break
            current = stack.pop()
            if isinstance(current, bool):
                total_count += 1
                continue
            numeric_value = self._coerce_number(current)
            if numeric_value is not None:
                numeric_count += 1
                total_count += 1
                continue
            if isinstance(current, dict):
                stack.extend(list(current.values()))
                continue
            if isinstance(current, list):
                stack.extend(current)
                continue
            total_count += 1

        return numeric_count, total_count

    def _has_numeric_series(self, value: Any, min_length: int) -> bool:
        """Detect list-of-dict numeric series."""
        stack = [value]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                stack.extend(list(current.values()))
                continue
            if isinstance(current, list):
                if self._list_has_numeric_series(current, min_length):
                    return True
                stack.extend(current)
        return False

    def _list_has_numeric_series(self, items: List[Any], min_length: int) -> bool:
        if len(items) < min_length:
            return False
        if all(self._coerce_number(item) is not None for item in items):
            return True
        numeric_key_counts: Dict[str, int] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            for key, value in item.items():
                if self._coerce_number(value) is not None:
                    numeric_key_counts[key] = numeric_key_counts.get(key, 0) + 1
        return any(count >= min_length for count in numeric_key_counts.values())

    def _coerce_number(self, value: Any) -> Optional[float]:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if cleaned.endswith("%"):
                cleaned = cleaned[:-1]
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _normalize_content(self, value: Any) -> Dict[str, Any]:
        """Normalize raw section data into a dictionary."""
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {"items": value}
        return {"value": value}

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
