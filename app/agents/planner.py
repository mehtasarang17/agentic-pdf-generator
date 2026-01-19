"""Planner Agent - Plans PDF structure and content layout."""

import json
import logging
from typing import Dict, Any, List

from app.agents.base import BaseAgent
from app.agents.state import AgentState, SectionPlan
from app.config import config

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Agent for planning PDF structure and content layout."""

    def __init__(self):
        super().__init__("Planner")

    def process(self, state: AgentState) -> AgentState:
        """Plan the PDF structure based on analyzed input.

        Args:
            state: Current agent state with sections_identified

        Returns:
            Updated state with section_plans and total_pages
        """
        if state.get('error') or not state.get('is_valid'):
            return state

        sections = state['sections_identified']
        client_name = state.get('client_name', 'Client')

        # Generate PDF title using LLM
        title = self._generate_title(sections, client_name)
        state['pdf_title'] = title

        # Plan sections
        section_plans = []
        current_page = 4  # Start after cover, disclaimer, and TOC

        for section in sections:
            plan = self._plan_section(section, current_page)
            section_plans.append(plan)
            current_page = plan['page_start'] + self._estimate_section_pages(section)

        # Ensure minimum 7 pages
        total_pages = max(current_page, config.MIN_PAGES)

        # If we need more pages, add padding or expand sections
        if total_pages < config.MIN_PAGES:
            section_plans = self._expand_sections(section_plans, config.MIN_PAGES - total_pages)
            total_pages = config.MIN_PAGES

        # Ensure maximum pages limit
        total_pages = min(total_pages, config.MAX_PAGES)

        state['section_plans'] = section_plans
        state['total_pages'] = total_pages

        self.logger.info(f"Planned {len(section_plans)} sections, {total_pages} total pages")

        return state

    def _generate_title(self, sections: List[Dict[str, Any]], client_name: str) -> str:
        """Generate PDF title using LLM.

        Args:
            sections: List of identified sections
            client_name: Client name

        Returns:
            Generated title string
        """
        section_names = [s.get('name', 'Section') for s in sections]
        section_summary = ", ".join(section_names)

        prompt = f"""Generate a professional PDF report title based on the following information:

Client: {client_name or 'Not Specified'}
Sections: {section_summary}

Requirements:
- Title should be concise (5-10 words)
- Professional and business-appropriate
- Reflect the content topics
- Do not include the client name in the title

Return ONLY the title text, nothing else."""

        try:
            title = self.invoke_llm(
                prompt,
                system_prompt="You are a professional document title generator.",
                max_tokens=50,
                temperature=0.5
            ).strip()

            # Clean up title
            title = title.strip('"\'')
            if not title:
                title = "Professional Report"

            return title
        except Exception as e:
            self.logger.warning(f"Failed to generate title: {e}")
            return "Professional Report"

    def _plan_section(self, section: Dict[str, Any], start_page: int) -> SectionPlan:
        """Plan a single section.

        Args:
            section: Section information
            start_page: Starting page number

        Returns:
            Section plan dictionary
        """
        section_type = section.get('type', 'descriptive')
        needs_chart = section_type == 'analytics'
        chart_type = None

        if needs_chart:
            chart_type = self._determine_chart_type(section.get('content', {}))

        return SectionPlan(
            name=section.get('name', 'Section'),
            type=section_type,
            content=section.get('content', {}),
            page_start=start_page,
            needs_chart=needs_chart,
            chart_type=chart_type
        )

    def _determine_chart_type(self, content: Dict[str, Any]) -> str:
        """Determine the best chart type for the content.

        Args:
            content: Section content

        Returns:
            Chart type string
        """
        if not content:
            return 'bar'

        # Count data points
        num_items = len(content)

        # Pie chart for small categorical data (2-6 items)
        if num_items <= 6 and all(isinstance(v, (int, float)) for v in content.values()):
            return 'pie'

        # Bar chart for moderate categorical data
        if num_items <= 12:
            return 'bar'

        # Line chart for sequential/time series data
        if any(isinstance(v, list) for v in content.values()):
            return 'line'

        # Radar chart for comparison data with multiple dimensions
        if num_items >= 3 and num_items <= 8:
            return 'radar'

        return 'bar'

    def _estimate_section_pages(self, section: Dict[str, Any]) -> int:
        """Estimate number of pages for a section.

        Args:
            section: Section information

        Returns:
            Estimated page count
        """
        content = section.get('content', {})
        content_size = len(json.dumps(content))

        # Base estimation: ~2000 chars per page
        text_pages = max(1, content_size // 2000)

        # Add page for chart if analytics
        if section.get('type') == 'analytics':
            text_pages += 1

        return text_pages

    def _expand_sections(self, plans: List[SectionPlan], pages_needed: int) -> List[SectionPlan]:
        """Expand sections to meet minimum page requirement.

        Args:
            plans: Current section plans
            pages_needed: Additional pages needed

        Returns:
            Updated section plans
        """
        # For now, we'll let the writer agent generate more content
        # The plans remain the same, but we note more content is needed
        return plans


# Singleton instance
planner_agent = PlannerAgent()
