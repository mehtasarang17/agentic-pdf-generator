"""LLM service wrapper - now uses OpenAI instead of AWS Bedrock."""

from app.services.llm_service import LLMService, llm_service

# Alias for backwards compatibility
BedrockService = LLMService
bedrock_service = llm_service
