"""AWS Bedrock LLM service wrapper."""

import logging
from typing import Optional, Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from app.config import config

logger = logging.getLogger(__name__)

try:
    from langchain_aws import ChatBedrockConverse
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:  # pragma: no cover - runtime dependency
    ChatBedrockConverse = None
    HumanMessage = None
    SystemMessage = None


class BedrockService:
    """Service for interacting with AWS Bedrock models."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        region: Optional[str] = None,
        bearer_token: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        session_token: Optional[str] = None
    ):
        self.model_id = model_id or config.BEDROCK_MODEL_ID
        self.region = region or config.BEDROCK_REGION
        self.bearer_token = bearer_token or config.AWS_BEARER_TOKEN_BEDROCK
        self.access_key_id = access_key_id or config.AWS_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or config.AWS_SECRET_ACCESS_KEY
        self.session_token = session_token or config.AWS_SESSION_TOKEN

        self.client = self._get_bedrock_client()
        self.llm = self._get_llm()

    def _get_bedrock_client(self):
        session_kwargs = {}
        if self.access_key_id and self.secret_access_key:
            session_kwargs["aws_access_key_id"] = self.access_key_id
            session_kwargs["aws_secret_access_key"] = self.secret_access_key
        if self.session_token:
            session_kwargs["aws_session_token"] = self.session_token
        if self.bearer_token and not session_kwargs:
            session_kwargs["aws_session_token"] = self.bearer_token
        if self.region:
            session_kwargs["region_name"] = self.region

        session = boto3.Session(**session_kwargs)
        return session.client(
            "bedrock-runtime",
            config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"})
        )

    def _get_llm(self):
        if ChatBedrockConverse is None:
            raise RuntimeError("langchain-aws is required for ChatBedrockConverse.")
        return ChatBedrockConverse(
            client=self.client,
            model=self.model_id,
            temperature=0.3,
            max_tokens=8000
        )

    def matches(self, model_id: str, region: str, bearer_token: Optional[str]) -> bool:
        return (
            self.model_id == model_id
            and self.region == region
            and self.bearer_token == bearer_token
        )

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """Invoke the Bedrock model with the given prompt."""
        try:
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            llm = self.llm.bind(max_tokens=max_tokens, temperature=temperature)
            response = llm.invoke(messages)
            return self._extract_message_content(response)
        except (BotoCoreError, ClientError, ValueError) as exc:
            logger.error("Error invoking Bedrock: %s", exc)
            raise

    def _extract_message_content(self, response: Any) -> str:
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                if parts:
                    return "".join(parts).strip()
            if isinstance(content, str):
                return content.strip()
        return str(response).strip()


# Singleton instance
bedrock_service = BedrockService()
