"""LLM 客户端 — OpenAI-compatible API (DeepSeek, 通义千问, GPT 等)。"""

import json
import logging

import httpx

from policymind.core.config import get_settings

logger = logging.getLogger(__name__)


async def llm_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """调用 LLM 聊天接口，返回文本回复。"""
    settings = get_settings()

    if not settings.LLM_API_KEY or settings.LLM_API_KEY == "change-me":
        raise RuntimeError("LLM_API_KEY 未配置，请在 .env 中填入 API Key")

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def llm_embed(texts: list[str]) -> list[list[float]]:
    """调用 Embedding 接口。"""
    settings = get_settings()

    if not settings.LLM_API_KEY or settings.LLM_API_KEY == "change-me":
        raise RuntimeError("LLM_API_KEY 未配置")

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.EMBEDDING_MODEL,
        "input": texts,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.LLM_BASE_URL}/embeddings",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        return [d["embedding"] for d in data["data"]]
