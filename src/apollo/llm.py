"""Chat model factory for the agents, backed by a Microsoft Foundry deployment."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

REQUIRED = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "APOLLO_CHAT_DEPLOYMENT")


def foundry_base_url(endpoint: str) -> str:
    """Accept either the resource endpoint or a full .../openai/v1 URL."""
    endpoint = endpoint.strip().rstrip("/")
    return endpoint if endpoint.endswith("/openai/v1") else f"{endpoint}/openai/v1"


@lru_cache(maxsize=4)
def get_chat_model(deployment: str | None = None, temperature: float = 0.0) -> BaseChatModel:
    """Return the chat model used by the coordinator and subagents."""
    load_dotenv()
    required = [name for name in REQUIRED if not (deployment and name == "APOLLO_CHAT_DEPLOYMENT")]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your Foundry deployment details."
        )
    return ChatOpenAI(
        model=deployment or os.environ["APOLLO_CHAT_DEPLOYMENT"],
        base_url=foundry_base_url(os.environ["AZURE_OPENAI_ENDPOINT"]),
        api_key=SecretStr(os.environ["AZURE_OPENAI_API_KEY"]),
        temperature=temperature,  # deterministic answers for legal and statistical lookups
        timeout=60,
        max_retries=0,  # retries are handled by ModelRetryMiddleware in Module 4
    )