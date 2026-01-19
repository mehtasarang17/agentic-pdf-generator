"""Content Builder Agent - Assembles final PDF content."""

import logging
from typing import Dict, Any, List

from app.agents.base import BaseAgent
from app.agents.state import AgentState
from app.services.pdf_service import pdf_service

logger = logging.getLogger(__name__)


class ContentBuilderAgent(BaseAgent):
    """Agent for assembling and building the final PDF."""

    def __init__(self):
        super().__init__("ContentBuilder")
        self.pdf_service = pdf_service

    def process(self, state: AgentState) -> AgentState:
        """Build the final PDF from all components.

        Args:
            state: Current agent state with all content

        Returns:
            Updated state with pdf_result
        """
        if state.get('error'):
            return state

        try:
            # Prepare sections content
            sections_content = self._prepare_sections(state)
            state['sections_content'] = sections_content

            # Generate PDF
            pdf_result = self.pdf_service.generate_pdf(
                title=state.get('pdf_title', 'Report'),
                client_name=state.get('client_name'),
                sections=sections_content,
                charts=state.get('charts', {})
            )

            state['pdf_result'] = pdf_result

            self.logger.info(
                f"Generated PDF: {pdf_result['pdf_id']} "
                f"with {len(sections_content)} sections"
            )

        except Exception as e:
            self.logger.error(f"Failed to build PDF: {e}")
            state['error'] = f"Failed to build PDF: {str(e)}"

        return state

    def _prepare_sections(self, state: AgentState) -> List[Dict[str, Any]]:
        """Prepare section content for PDF generation.

        Args:
            state: Current agent state

        Returns:
            List of section dictionaries ready for PDF service
        """
        section_plans = state.get('section_plans', [])
        descriptions = state.get('generated_descriptions', {})
        summaries = state.get('section_summaries', {})

        sections = []

        for plan in section_plans:
            section_name = plan['name']
            original_content = plan['content']

            # Build section content
            content = {
                'description': descriptions.get(section_name, ''),
                'data': original_content if plan['type'] == 'analytics' else None,
            }

            # Add text content for descriptive sections
            if plan['type'] == 'descriptive':
                content['text'] = self._extract_text_content(original_content)
                content['bullets'] = self._extract_bullets(original_content)
                content['findings'] = self._extract_findings(original_content)

            # Clean up None values
            content = {k: v for k, v in content.items() if v is not None}

            sections.append({
                'name': section_name,
                'content': content
            })

        return sections

    def _extract_text_content(self, content: Dict[str, Any]) -> List[str]:
        """Extract text content from section data.

        Args:
            content: Section content dictionary

        Returns:
            List of text paragraphs
        """
        text_items = []
        skip_keys = {'bullets', 'points', 'items', 'list', 'findings', 'data'}

        for key, value in content.items():
            if key in skip_keys:
                continue
            if isinstance(value, str):
                text_items.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        text_items.append(item)

        return text_items if text_items else None

    def _extract_bullets(self, content: Dict[str, Any]) -> List[str]:
        """Extract bullet points from section data.

        Args:
            content: Section content dictionary

        Returns:
            List of bullet points
        """
        # Look for common bullet point keys
        bullet_keys = ['bullets', 'points', 'items', 'list']

        for key in bullet_keys:
            if key in content and isinstance(content[key], list):
                return content[key]

        return None

    def _extract_findings(self, content: Dict[str, Any]) -> List[str]:
        """Extract findings from section data.

        Args:
            content: Section content dictionary

        Returns:
            List of findings
        """
        # Look for findings key
        if 'findings' in content and isinstance(content['findings'], list):
            return content['findings']

        return None


# Singleton instance
content_builder_agent = ContentBuilderAgent()
