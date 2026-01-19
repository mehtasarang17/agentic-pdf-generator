"""Visualizer Agent - Generates charts and visualizations."""

import logging
from typing import Dict, Any, List

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.services.chart_service import chart_service

logger = logging.getLogger(__name__)


class VisualizerAgent(BaseAgent):
    """Agent for creating data visualizations."""

    def __init__(self):
        super().__init__("Visualizer")
        self.chart_service = chart_service

    def process(self, state: AgentState) -> AgentState:
        """Generate charts for analytics sections.

        Args:
            state: Current agent state with section_plans

        Returns:
            Updated state with charts dictionary
        """
        if state.get('error'):
            return state

        section_plans = state.get('section_plans', [])
        charts = {}

        for plan in section_plans:
            if not plan.get('needs_chart'):
                continue

            section_name = plan['name']
            content = plan['content']
            chart_type = plan.get('chart_type', 'bar')

            try:
                chart_bytes = self._create_chart(section_name, content, chart_type)
                if chart_bytes:
                    charts[section_name] = [chart_bytes]
                    self.logger.debug(f"Created {chart_type} chart for {section_name}")
            except Exception as e:
                self.logger.error(f"Failed to create chart for {section_name}: {e}")

        state['charts'] = charts

        self.logger.info(f"Generated {len(charts)} charts")

        return state

    def _create_chart(
        self,
        section_name: str,
        content: Dict[str, Any],
        chart_type: str
    ) -> bytes:
        """Create a chart for the given content.

        Args:
            section_name: Name of the section
            content: Data content for the chart
            chart_type: Type of chart to create

        Returns:
            PNG image bytes
        """
        # Flatten nested content for charting
        chart_data = self._prepare_chart_data(content)

        if not chart_data:
            self.logger.warning(f"No chartable data in {section_name}")
            return None

        # Generate chart title
        title = f"{section_name}"

        return self.chart_service.create_chart(
            chart_type=chart_type,
            data=chart_data,
            title=title
        )

    def _prepare_chart_data(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare content data for charting.

        Args:
            content: Raw content dictionary

        Returns:
            Flattened dictionary suitable for charting
        """
        chart_data = {}

        for key, value in content.items():
            if isinstance(value, (int, float)):
                # Use formatted key name
                formatted_key = key.replace('_', ' ').title()
                chart_data[formatted_key] = value
            elif isinstance(value, dict):
                # Handle nested dictionaries
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, (int, float)):
                        formatted_key = f"{key} - {nested_key}".replace('_', ' ').title()
                        chart_data[formatted_key] = nested_value
            elif isinstance(value, list) and all(isinstance(v, (int, float)) for v in value):
                # Handle list of numbers
                formatted_key = key.replace('_', ' ').title()
                chart_data[formatted_key] = value

        return chart_data

    def _detect_best_chart_type(self, content: Dict[str, Any]) -> str:
        """Detect the best chart type for the content.

        Args:
            content: Data content

        Returns:
            Chart type string
        """
        chart_data = self._prepare_chart_data(content)

        if not chart_data:
            return 'bar'

        num_items = len(chart_data)
        values = list(chart_data.values())

        # Check for list values (time series)
        if any(isinstance(v, list) for v in values):
            return 'line'

        # Pie chart for small datasets with positive values
        if num_items <= 6 and all(v > 0 for v in values if isinstance(v, (int, float))):
            return 'pie'

        # Radar for moderate datasets
        if 3 <= num_items <= 8:
            return 'radar'

        return 'bar'


# Singleton instance
visualizer_agent = VisualizerAgent()
