"""Visualizer Agent - Generates charts and visualizations."""

import logging
from typing import Dict, Any, List, Optional, Tuple

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.config import config
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
            section_name = plan['name']
            content = plan['content']
            chart_type = plan.get('chart_type', 'bar')

            try:
                chart_bytes, resolved_type = self._create_chart(
                    section_name,
                    content,
                    chart_type
                )
                if chart_bytes:
                    charts[section_name] = [chart_bytes]
                    self.logger.debug(
                        "Created %s chart for %s",
                        resolved_type or chart_type,
                        section_name
                    )
                else:
                    self.logger.debug(
                        "No chartable data for section '%s'; skipping chart.",
                        section_name
                    )
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
    ) -> Tuple[Optional[bytes], Optional[str]]:
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
            return None, None

        resolved_type = self._resolve_chart_type(chart_data, chart_type)
        if not self._has_chartable_points(chart_data, resolved_type):
            self.logger.warning(
                "Skipping chart for %s due to insufficient data points.",
                section_name
            )
            return None, None

        chart_bytes = self.chart_service.create_chart(
            chart_type=resolved_type,
            data=chart_data,
            title=f"{section_name}"
        )
        return chart_bytes, resolved_type

    def _prepare_chart_data(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare content data for charting.

        Args:
            content: Raw content dictionary

        Returns:
            Flattened dictionary suitable for charting
        """
        chart_data: Dict[str, Any] = {}
        if not isinstance(content, dict):
            content = {"value": content}

        for key, value in content.items():
            self._merge_chart_data(chart_data, key, value)

        return self._trim_chart_data(chart_data)

    def _merge_chart_data(self, chart_data: Dict[str, Any], key: str, value: Any) -> None:
        formatted_key = key.replace('_', ' ').title()
        numeric_value = self._coerce_number(value)
        if numeric_value is not None:
            chart_data[formatted_key] = numeric_value
            return

        if isinstance(value, dict):
            nested_numeric = {}
            for nested_key, nested_value in value.items():
                numeric_nested = self._coerce_number(nested_value)
                if numeric_nested is not None:
                    nested_key_fmt = f"{key} - {nested_key}".replace('_', ' ').title()
                    nested_numeric[nested_key_fmt] = numeric_nested
            if nested_numeric:
                chart_data.update(nested_numeric)
                return
            for nested_key, nested_value in value.items():
                self._merge_chart_data(
                    chart_data,
                    f"{key} - {nested_key}",
                    nested_value
                )
            return

        if isinstance(value, list):
            self._merge_list_data(chart_data, formatted_key, value)

    def _merge_list_data(self, chart_data: Dict[str, Any], key: str, items: List[Any]) -> None:
        if not items:
            return
        numeric_items = [self._coerce_number(item) for item in items]
        if all(item is not None for item in numeric_items):
            series = [item for item in numeric_items if item is not None]
            chart_data[key] = series[:config.VISUALIZER_MAX_SERIES_ITEMS]
            return
        if all(isinstance(item, dict) for item in items):
            label_values = self._extract_label_value_pairs(items, key)
            if label_values:
                chart_data.update(label_values)
                return
            aggregated = self._aggregate_numeric_fields(items)
            if aggregated:
                for agg_key, agg_value in aggregated.items():
                    chart_data[f"{key} - {agg_key}"] = agg_value

    def _extract_label_value_pairs(
        self,
        items: List[Dict[str, Any]],
        prefix: str
    ) -> Dict[str, float]:
        label_keys = ["name", "title", "id", "label", "category", "type", "severity", "status"]
        value_keys = ["count", "total", "value", "score", "cvss", "amount", "risk", "severity_score"]

        label_key = self._first_matching_key(items, label_keys, expect_numeric=False)
        value_key = self._first_matching_key(items, value_keys, expect_numeric=True)

        if label_key is None:
            label_key = self._first_string_key(items)
        if value_key is None:
            value_key = self._first_numeric_key(items)

        if label_key is None or value_key is None:
            return {}

        label_values: List[Tuple[str, float]] = []
        for item in items:
            label = item.get(label_key)
            numeric = self._coerce_number(item.get(value_key))
            if isinstance(label, str) and numeric is not None:
                label_values.append((label.strip(), numeric))

        if not label_values:
            return {}

        label_values.sort(key=lambda pair: pair[1], reverse=True)
        label_values = label_values[:config.VISUALIZER_MAX_CATEGORIES]
        return {f"{prefix}: {label}": value for label, value in label_values}

    def _aggregate_numeric_fields(self, items: List[Dict[str, Any]]) -> Dict[str, float]:
        aggregates: Dict[str, float] = {}
        for item in items:
            for key, value in item.items():
                numeric = self._coerce_number(value)
                if numeric is None:
                    continue
                aggregates[key] = aggregates.get(key, 0.0) + numeric
        if not aggregates:
            return {}
        sorted_items = sorted(aggregates.items(), key=lambda pair: pair[1], reverse=True)
        sorted_items = sorted_items[:config.VISUALIZER_MAX_CATEGORIES]
        return dict(sorted_items)

    def _first_matching_key(
        self,
        items: List[Dict[str, Any]],
        keys: List[str],
        expect_numeric: bool
    ) -> Optional[str]:
        for key in keys:
            for item in items:
                if key not in item:
                    continue
                value = item.get(key)
                if expect_numeric and self._coerce_number(value) is not None:
                    return key
                if not expect_numeric and isinstance(value, str):
                    return key
        return None

    def _first_string_key(self, items: List[Dict[str, Any]]) -> Optional[str]:
        for item in items:
            for key, value in item.items():
                if isinstance(value, str):
                    return key
        return None

    def _first_numeric_key(self, items: List[Dict[str, Any]]) -> Optional[str]:
        for item in items:
            for key, value in item.items():
                if self._coerce_number(value) is not None:
                    return key
        return None

    def _trim_chart_data(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        if not chart_data:
            return {}
        if any(isinstance(value, list) for value in chart_data.values()):
            return chart_data
        items = sorted(
            chart_data.items(),
            key=lambda pair: pair[1],
            reverse=True
        )
        items = items[:config.VISUALIZER_MAX_CATEGORIES]
        return dict(items)

    def _resolve_chart_type(self, chart_data: Dict[str, Any], chart_type: str) -> str:
        if chart_type and chart_type.lower() not in {"bar", "pie", "line", "radar"}:
            chart_type = None
        if any(isinstance(value, list) for value in chart_data.values()):
            return "line"
        if not chart_type:
            return self._detect_best_chart_type(chart_data)
        return chart_type.lower()

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

    def _has_chartable_points(self, chart_data: Dict[str, Any], chart_type: str) -> bool:
        if not chart_data:
            return False
        if chart_type == "line":
            max_len = 0
            for value in chart_data.values():
                if isinstance(value, list):
                    max_len = max(max_len, len(value))
                else:
                    max_len = max(max_len, 1)
            return max_len >= 2
        return len(chart_data) >= 2

    def _detect_best_chart_type(self, chart_data: Dict[str, Any]) -> str:
        """Detect the best chart type for prepared chart data."""
        if not chart_data:
            return 'bar'

        num_items = len(chart_data)
        values = list(chart_data.values())

        if any(isinstance(v, list) for v in values):
            return 'line'

        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if num_items <= 6 and numeric_values and all(v > 0 for v in numeric_values):
            return 'pie'
        if 3 <= num_items <= 8:
            return 'radar'
        return 'bar'


# Singleton instance
visualizer_agent = VisualizerAgent()
