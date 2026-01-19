"""Base agent class with common functionality."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

from app.agents.state import AgentState
from app.services.bedrock_service import bedrock_service

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the PDF generation workflow."""

    def __init__(self, name: str):
        """Initialize the agent.

        Args:
            name: Agent name for logging and identification
        """
        self.name = name
        self.llm = bedrock_service
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def process(self, state: AgentState) -> AgentState:
        """Process the current state and return updated state.

        Args:
            state: Current agent state

        Returns:
            Updated agent state
        """
        pass

    def __call__(self, state: AgentState) -> AgentState:
        """Make agent callable for LangGraph integration."""
        self.logger.info(f"Agent {self.name} processing...")
        try:
            result = self.process(state)
            self.logger.info(f"Agent {self.name} completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed: {e}")
            state['error'] = f"Agent {self.name} failed: {str(e)}"
            return state

    def invoke_llm(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """Invoke the LLM with the given prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            LLM response text
        """
        return self.llm.invoke(prompt, system_prompt, max_tokens, temperature)
