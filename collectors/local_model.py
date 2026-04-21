"""Example local model collector for the hallucination detector.

This module demonstrates how to add a new collector with ZERO changes to
existing system components. Simply create a new collector file that:

1. Inherits from BaseCollector
2. Implements the get_response() method
3. Auto-registers itself at import time

The system automatically discovers and uses it.

This collector is disabled by default and provided as an example.
To enable it, uncomment the auto-registration code at the bottom.
"""

import asyncio
import time
from typing import Optional, Dict, Any

from core import BaseCollector, get_registry


class LocalModelCollector(BaseCollector):
    """Example local model collector (e.g., Ollama, LLaMA.cpp, etc.).

    This is a stub implementation showing how to add a new model.
    In production, this would interface with a local inference engine.

    Features:
        - No external API calls required
        - Runs locally on machine
        - Fast inference for demonstration
    """

    @property
    def model_name(self) -> str:
        """Return the model identifier: 'local'."""
        return "local"

    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch a response from a local model.

        Args:
            query: The user's query
            context: Optional context information

        Returns:
            Dict[str, Any]: Standardized response schema
        """
        started_at = time.monotonic()

        # Simulate local model inference
        # In production, replace with actual model inference code
        try:
            # Example: simulate processing delay
            await asyncio.sleep(0.1)

            response_text = f"[Local model response to: {query}]"

            success = True
            error = None
        except Exception as exc:
            response_text = ""
            success = False
            error = str(exc).strip() or "Local model error"

        latency_ms = int((time.monotonic() - started_at) * 1000)
        return {
            "model": self.model_name,
            "response": response_text if success else "",
            "success": success,
            "error": error,
            "latency_ms": latency_ms,
        }


# EXTENSIBILITY TEST: Uncomment the following lines to automatically
# register this collector. No other changes needed anywhere!
# _local_collector = LocalModelCollector()
# get_registry().register(_local_collector)
