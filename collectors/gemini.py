"""Gemini collector module for the hallucination detector.

This module wraps the Google Gemini API in a thread-safe async interface.
It inherits from BaseCollector and auto-registers with the global registry.
"""

import asyncio
import time
from functools import partial
from typing import Optional, Dict, Any

import google.generativeai as genai

from config import GEMINI_API_KEY
from core import BaseCollector, get_registry

MODEL_NAME = "models/gemini-1.5-flash"
TIMEOUT_SECONDS = 10.0
MAX_TOKENS = 500

# Configure the Gemini client at import time using the project config.
genai.configure(api_key=GEMINI_API_KEY)


def _build_prompt(query: str, context: Optional[str] = None) -> str:
    """Build the prompt text for Gemini based on optional context."""
    if context and context.strip():
        return f"Context: {context.strip()}\n\nQuestion: {query.strip()}"
    return query.strip()


def _extract_text(payload: Any) -> str:
    """Extract text from the Gemini response payload."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload.strip()
    if hasattr(payload, "text"):
        return str(getattr(payload, "text")).strip()
    if isinstance(payload, dict):
        for key in ("text", "response", "output", "content"):
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


def _sync_gemini_call(prompt: str) -> Any:
    """Perform the synchronous Gemini API call."""
    return genai.generate_text(
        model=MODEL_NAME,
        prompt=prompt,
        max_output_tokens=MAX_TOKENS,
    )


async def _invoke_with_retry(prompt: str) -> Any:
    """Invoke Gemini in a thread pool with retry and timeout handling."""
    last_exception: Optional[Exception] = None
    loop = asyncio.get_running_loop()
    for attempt in range(2):
        try:
            call = partial(_sync_gemini_call, prompt)
            return await asyncio.wait_for(loop.run_in_executor(None, call), timeout=TIMEOUT_SECONDS)
        except Exception as exc:
            last_exception = exc
            if attempt == 1:
                raise last_exception
    raise RuntimeError("Gemini retry logic failed")


class GeminiCollector(BaseCollector):
    """Google Gemini model collector.

    This collector interfaces with Google's Gemini models to fetch responses.
    It handles timeouts, retries, and exception safety as required by the
    BaseCollector contract. Gemini's synchronous API is wrapped in a thread pool
    to keep it non-blocking.

    Features:
        - Async/await support
        - 10-second timeout with automatic retry
        - Synchronous Gemini API wrapped in thread pool
        - Exception safety: never raises, always returns normalized schema
        - Latency tracking
    """

    @property
    def model_name(self) -> str:
        """Return the model identifier: 'gemini'."""
        return "gemini"

    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch a response from Gemini.

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
                error = "Empty response from gemini"
            else:
                success = True
        except Exception as exc:
            error = str(exc).strip() or "Unknown gemini error"

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
    """Get a normalized response from Gemini while keeping the event loop non-blocking.

    This function is provided for backward compatibility.
    New code should use GeminiCollector directly.
    """
    collector = GeminiCollector()
    return await collector.get_response(query, context)


# Auto-register the collector at import time
_gemini_collector = GeminiCollector()
get_registry().register(_gemini_collector)