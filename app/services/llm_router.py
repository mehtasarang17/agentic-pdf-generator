"""Route LLM calls to OpenAI or Bedrock based on request context."""

from contextvars import ContextVar
from typing import Any, Dict, Optional

from app.config import config
from app.services.llm_service import llm_service
from app.services.bedrock_service import BedrockService

_LLM_CONTEXT: ContextVar[Dict[str, Any]] = ContextVar("llm_context", default={})


def set_llm_context(context: Dict[str, Any]):
    """Set per-request LLM context (provider, model, credentials)."""
    return _LLM_CONTEXT.set(context or {})


def reset_llm_context(token) -> None:
    """Reset LLM context to previous value."""
    _LLM_CONTEXT.reset(token)


def get_llm_context() -> Dict[str, Any]:
    """Get the current LLM context."""
    return _LLM_CONTEXT.get() or {}


class LLMRouter:
    """Provider-aware LLM dispatcher."""

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        context = get_llm_context()
        provider = (context.get("provider") or "bedrock").lower()
        model = context.get("model")

        if provider == "openai":
            api_key = context.get("openai_api_key") or config.OPENAI_API_KEY
            model = model or config.OPENAI_MODEL
            return llm_service.invoke(
                prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                api_key=api_key,
                model=model
            )

        bearer_token = context.get("bedrock_bearer_token") or config.AWS_BEARER_TOKEN_BEDROCK
        region = context.get("bedrock_region") or config.BEDROCK_REGION
        model = model or config.BEDROCK_MODEL_ID

        service = context.get("_bedrock_service")
        if not isinstance(service, BedrockService) or not service.matches(model, region, bearer_token):
            service = BedrockService(
                model_id=model,
                region=region,
                bearer_token=bearer_token
            )
            context["_bedrock_service"] = service

        return service.invoke(
            prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )


llm_router = LLMRouter()
