"""Writer Agent - Generates LLM-based descriptions and content."""

import json
import logging
from typing import Dict, Any, List

from app.agents.base import BaseAgent
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Agent for generating text content using LLM."""

    def __init__(self):
        super().__init__("Writer")

    def process(self, state: AgentState) -> AgentState:
        """Generate descriptions for descriptive sections.

        Args:
            state: Current agent state with section_plans

        Returns:
            Updated state with generated_descriptions
        """
        if state.get('error'):
            return state

        section_plans = state.get('section_plans', [])
        generated_descriptions = {}
        section_summaries = {}

        for plan in section_plans:
            section_name = plan['name']
            section_type = plan['type']
            content = plan['content']

            # Generate description for all sections
            description = self._generate_description(section_name, content, section_type)
            generated_descriptions[section_name] = description

            # Generate summary
            summary = self._generate_summary(section_name, content)
            section_summaries[section_name] = summary

            self.logger.debug(f"Generated content for section: {section_name}")

        state['generated_descriptions'] = generated_descriptions
        state['section_summaries'] = section_summaries

        self.logger.info(f"Generated descriptions for {len(generated_descriptions)} sections")

        return state

    def _generate_description(
        self,
        section_name: str,
        content: Dict[str, Any],
        section_type: str
    ) -> str:
        """Generate a description for a section.

        Args:
            section_name: Name of the section
            content: Section content
            section_type: Type of section ('analytics' or 'descriptive')

        Returns:
            Generated description text
        """
        content_str = json.dumps(content, indent=2)

        if section_type == 'analytics':
            prompt = f"""Write a professional analysis description for the following data section of a business report.

Section Name: {section_name}
Data:
{content_str}

Requirements:
- Write 2-3 paragraphs analyzing the data
- Highlight key trends, patterns, or notable values
- Use professional business language
- Include specific numbers and percentages where relevant
- Do not use markdown formatting

Write the analysis now:"""
        else:
            prompt = f"""Write a professional description for the following section of a business report.

Section Name: {section_name}
Content:
{content_str}

Requirements:
- Write 2-3 paragraphs elaborating on this content
- Maintain professional business language
- Expand on key points with additional context
- Make the content informative and engaging
- Do not use markdown formatting

Write the description now:"""

        try:
            description = self.invoke_llm(
                prompt,
                system_prompt="You are a professional technical writer creating content for business reports. Write clear, informative, and professional content.",
                max_tokens=1500,
                temperature=0.7
            )

            return description.strip()
        except Exception as e:
            self.logger.error(f"Failed to generate description: {e}")
            return f"This section covers {section_name}."

    def _generate_summary(self, section_name: str, content: Dict[str, Any]) -> str:
        """Generate a brief summary for a section.

        Args:
            section_name: Name of the section
            content: Section content

        Returns:
            Brief summary text
        """
        content_str = json.dumps(content, indent=2)

        prompt = f"""Write a one-sentence summary for the following section:

Section Name: {section_name}
Content:
{content_str}

Return ONLY the summary sentence, nothing else."""

        try:
            summary = self.invoke_llm(
                prompt,
                system_prompt="You are a concise technical writer.",
                max_tokens=100,
                temperature=0.5
            )
            return summary.strip()
        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return f"Summary of {section_name}."

    def _generate_introduction(self, title: str, sections: List[str]) -> str:
        """Generate an introduction for the document.

        Args:
            title: Document title
            sections: List of section names

        Returns:
            Introduction text
        """
        sections_str = ", ".join(sections)

        prompt = f"""Write a professional introduction paragraph for a business report with the following details:

Title: {title}
Sections covered: {sections_str}

Requirements:
- One paragraph, 3-4 sentences
- Professional tone
- Briefly introduce what the report covers
- Do not use markdown formatting

Write the introduction:"""

        try:
            intro = self.invoke_llm(
                prompt,
                system_prompt="You are a professional technical writer.",
                max_tokens=200,
                temperature=0.7
            )
            return intro.strip()
        except Exception as e:
            self.logger.error(f"Failed to generate introduction: {e}")
            return f"This report provides a comprehensive analysis of {sections_str}."


# Singleton instance
writer_agent = WriterAgent()
