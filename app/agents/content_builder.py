"""Content Builder Agent - Assembles final PDF content."""

import logging
from typing import Dict, Any, List, Optional

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
        generated_bullets = state.get('generated_bullets', {})
        generated_findings = state.get('generated_findings', {})
        summaries = state.get('section_summaries', {})
        section_parts = state.get('section_parts', {})

        sections = []

        for plan in section_plans:
            section_name = plan['name']
            original_content = plan['content']

            # Build section content
            content = {
                'description': descriptions.get(section_name, ''),
                'data': original_content if plan['type'] == 'analytics' else None,
            }

            text_content = self._extract_text_content(original_content)
            if text_content:
                content['text'] = text_content

            llm_bullets = self._sanitize_bullets(generated_bullets.get(section_name))
            extracted_bullets = self._sanitize_bullets(
                self._extract_bullets(original_content)
            )
            if llm_bullets:
                content['bullets'] = llm_bullets
            elif extracted_bullets:
                content['bullets'] = extracted_bullets

            llm_findings = self._sanitize_bullets(generated_findings.get(section_name))
            extracted_findings = self._sanitize_bullets(
                self._extract_findings(original_content)
            )
            if llm_findings:
                content['findings'] = llm_findings
            elif extracted_findings:
                content['findings'] = extracted_findings

            # Clean up None values
            content = {k: v for k, v in content.items() if v is not None}

            sections.append({
                'name': section_name,
                'content': content
            })

            parts = section_parts.get(section_name) or []
            if len(parts) > 1:
                for idx, part in enumerate(parts, start=1):
                    part_content = {
                        'description': part.get('description', '')
                    }
                    part_bullets = self._sanitize_bullets(part.get('bullets'))
                    if part_bullets:
                        part_content['bullets'] = part_bullets

                    part_findings = self._sanitize_bullets(part.get('findings'))
                    if part_findings:
                        part_content['findings'] = part_findings

                    sections.append({
                        'name': f"{section_name} (Part {idx})",
                        'content': part_content
                    })

        return sections

    def _sanitize_bullets(self, bullets: Any) -> Optional[List[str]]:
        """Filter bullets to simple strings to avoid rendering raw tables."""
        if not bullets:
            return None
        if not isinstance(bullets, list):
            bullets = [bullets]

        cleaned = []
        for bullet in bullets:
            if isinstance(bullet, bool):
                continue
            if isinstance(bullet, (int, float, str)):
                text = str(bullet).strip()
                if text:
                    cleaned.append(text)
        return cleaned or None

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
