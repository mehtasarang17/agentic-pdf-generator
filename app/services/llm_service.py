"""OpenAI LLM service for text generation."""

import json
import logging
from typing import Optional

from openai import OpenAI

from app.config import config

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with OpenAI GPT models."""

    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """
        Invoke the OpenAI LLM with a prompt.

        Args:
            prompt: The user prompt to send
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            The LLM response text
        """
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Error invoking OpenAI: {e}")
            raise

    def generate_title(self, content_summary: str) -> str:
        """Generate a professional PDF title based on content."""
        prompt = f"""Based on the following content summary, generate a professional and concise title for a PDF report.
The title should be clear, informative, and suitable for a business document.
Return ONLY the title text, nothing else.

Content Summary:
{content_summary}"""

        system_prompt = "You are a professional document title generator. Generate concise, clear, and professional titles."
        return self.invoke(prompt, system_prompt, max_tokens=100, temperature=0.5).strip()

    def generate_description(self, section_name: str, content: dict) -> str:
        """Generate a descriptive text for a section."""
        prompt = f"""Write a professional description for the following section of a business report.
The description should be informative, well-structured, and suitable for a professional PDF document.

Section Name: {section_name}
Content: {json.dumps(content, indent=2)}

Write 2-3 paragraphs that explain and elaborate on this content."""

        system_prompt = "You are a professional technical writer creating content for business reports."
        return self.invoke(prompt, system_prompt, max_tokens=1000, temperature=0.7)

    def analyze_data_for_visualization(self, data: dict) -> dict:
        """Analyze data and recommend visualization type."""
        prompt = f"""Analyze the following data and recommend the best chart type for visualization.
Return a JSON object with the following fields:
- chart_type: one of "bar", "line", "pie", "radar"
- title: suggested chart title
- reason: brief explanation

Data:
{json.dumps(data, indent=2)}

Return ONLY valid JSON, no additional text."""

        system_prompt = "You are a data visualization expert. Respond only with valid JSON."
        response = self.invoke(prompt, system_prompt, max_tokens=200, temperature=0.3)

        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            return json.loads(response)
        except json.JSONDecodeError:
            return {"chart_type": "bar", "title": "Data Visualization", "reason": "Default"}


# Singleton instance
llm_service = LLMService()
