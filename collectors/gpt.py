"""GPT collector module for the hallucination detector.

This module provides an async wrapper around the OpenAI GPT model.
It implements BaseCollector and is registered in the collectors/registry.py.
"""

import asyncio
import time
from typing import Optional, Dict, Any

from openai import AsyncOpenAI

from config import OPENAI_API_KEY
from collectors.base import BaseCollector

MODEL_NAME = "gpt-4o-mini"
TIMEOUT_SECONDS = 10.0
MAX_TOKENS = 500


def _build_prompt(query: str, context: Optional[str] = None) -> str:
    """Build the prompt text for GPT based on optional context."""
    if context and context.strip():
        return f"Context: {context.strip()}\n\nQuestion: {query.strip()}"
    return query.strip()


def _extract_text(payload: Any) -> str:
    """Extract text from the OpenAI response payload."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        for key in ("text", "content", "message", "output", "completion", "response"):
            if key in payload:
                text = _extract_text(payload[key])
                if text:
                    return text
        for value in payload.values():
            text = _extract_text(value)
            if text:
                return text
        return ""
    if isinstance(payload, list):
        for item in payload:
            text = _extract_text(item)
            if text:
                return text
        return ""
    return str(payload).strip()


async def _call_gpt(prompt: str) -> Any:
    """Perform the GPT async API call and return the raw API response."""
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return await client.completions.create(
        model=MODEL_NAME,
        prompt=prompt,
        max_tokens=MAX_TOKENS,
    )


async def _invoke_with_retry(prompt: str) -> Any:
    """Invoke GPT with one retry and timeout handling."""
    last_exception: Optional[Exception] = None
    for attempt in range(2):
        try:
            return await asyncio.wait_for(_call_gpt(prompt), timeout=TIMEOUT_SECONDS)
        except Exception as exc:
            last_exception = exc
            if attempt == 1:
                raise last_exception
    raise RuntimeError("GPT retry logic failed")


class GPTCollector(BaseCollector):
    """OpenAI GPT model collector.

    This collector interfaces with OpenAI's GPT models to fetch responses.
    It handles timeouts, retries, and exception safety as required by the
    BaseCollector contract.

    Features:
        - Async/await support
        - 10-second timeout with automatic retry
        - Exception safety: never raises, always returns normalized schema
        - Latency tracking
    """

    @property
    def model_name(self) -> str:
        """Return the model identifier: 'gpt'."""
        return "gpt"

    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch a response from GPT.

        Args:
            query: The user's query
            context: Optional context information

        Returns:
            Dict[str, Any]: Standardized response schema
        """
        started_at = time.monotonic()
        prompt = _build_prompt(query, context)
        response_text: str = ""
        error: Optional[str] = None
        success = False

        try:
            api_response = await _invoke_with_retry(prompt)
            response_text = _extract_text(api_response)
            if not response_text:
                error = "Empty response from gpt"
            else:
                success = True
        except Exception as exc:
            error = str(exc).strip() or "Unknown gpt error"

        latency_ms = int((time.monotonic() - started_at) * 1000)
        return {
            "model": self.model_name,
            "response": response_text if success else "",
            "success": success,
            "error": error,
            "latency_ms": latency_ms,
        }


# Backward-compatible function interface
async def get_response(query: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Get a normalized response from GPT without exposing raw response details.

    This function is provided for backward compatibility.
    New code should use GPTCollector directly.
    """
    collector = GPTCollector()
    return await collector.get_response(query, context)