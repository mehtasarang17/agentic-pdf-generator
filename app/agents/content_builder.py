"""Content Builder Agent - Assembles final PDF content."""

import logging
import re
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
        table_value_summaries = state.get('table_value_summaries', {})

        sections = []

        for plan in section_plans:
            section_name = plan['name']
            original_content = plan['content']
            summarized_values = table_value_summaries.get(section_name, {})

            # Build section content
            content = {
                'description': descriptions.get(section_name, ''),
                'data': (
                    self._apply_table_summaries(original_content, summarized_values)
                    if plan['type'] == 'analytics'
                    else None
                ),
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

    def _apply_table_summaries(
        self,
        data: Dict[str, Any],
        summaries: Dict[str, str]
    ) -> Dict[str, Any]:
        if not isinstance(data, dict) or not summaries:
            return data
        summarized = {}
        for key, value in data.items():
            if key in summaries:
                summarized[key] = summaries[key]
            else:
                summarized[key] = value
        return summarized

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
            if isinstance(bullet, (int, float)):
                continue
            if isinstance(bullet, str):
                text = bullet.strip()
                if text and not self._is_numeric_text(text):
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
                if not self._is_narrative_key(key):
                    continue
                cleaned = value.strip()
                if (
                    cleaned
                    and not self._is_numeric_text(cleaned)
                    and not self._is_standalone_value_text(cleaned)
                ):
                    text_items.append(cleaned)
            elif isinstance(value, list):
                if not self._is_narrative_key(key):
                    continue
                for item in value:
                    if isinstance(item, str):
                        cleaned = item.strip()
                        if (
                            cleaned
                            and not self._is_numeric_text(cleaned)
                            and not self._is_standalone_value_text(cleaned)
                        ):
                            text_items.append(cleaned)

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

    def _is_numeric_text(self, text: str) -> bool:
        """Return True if text is just a number (optionally with %)."""
        cleaned = text.strip().replace(",", "")
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1].strip()
        try:
            float(cleaned)
            return True
        except ValueError:
            return False

    def _is_standalone_value_text(self, text: str) -> bool:
        """Return True for single-token values like IDs or timestamps."""
        cleaned = text.strip()
        if not cleaned:
            return True
        if any(ch.isspace() for ch in cleaned):
            return False
        if self._is_iso_timestamp(cleaned):
            return True
        lowered = cleaned.lower()
        if lowered in {"ok", "true", "false", "yes", "no", "none", "null", "unknown"}:
            return True
        if lowered.startswith("http://") or lowered.startswith("https://"):
            return True
        if len(cleaned) >= 8 and all(ch.isalnum() or ch in "-_" for ch in cleaned):
            return True
        return False

    def _is_iso_timestamp(self, text: str) -> bool:
        """Return True if text matches common ISO-8601 timestamp formats."""
        iso_patterns = (
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z$",
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\+\-]\d{2}:\d{2}$",
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
        )
        return any(re.match(pattern, text) for pattern in iso_patterns)

    def _is_narrative_key(self, key: str) -> bool:
        """Return True if key likely contains narrative text."""
        lowered = key.lower()
        narrative_keys = (
            "description",
            "summary",
            "overview",
            "details",
            "narrative",
            "notes",
            "comment",
            "analysis",
            "text",
            "message",
        )
        return any(token in lowered for token in narrative_keys)


# Singleton instance
content_builder_agent = ContentBuilderAgent()
