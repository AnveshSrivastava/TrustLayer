"""Base collector interface for the hallucination detector.

This module defines the abstract base class that all collectors must inherit from.
It enforces a strict contract ensuring all collectors return standardized responses.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseCollector(ABC):
    """Abstract base class for all LLM collectors.

    Enforces a strict interface contract: all collectors must implement
    `get_response()` and return a standardized schema.

    All collectors must return:
    {
        "model": str,           # Model identifier
        "response": str,        # Normalized text response
        "success": bool,        # Whether the call succeeded
        "error": Optional[str], # Error message if failed
        "latency_ms": int       # Latency in milliseconds
    }

    This ensures loose coupling: the orchestrator and other components
    interact with collectors purely through this interface.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the unique identifier for this collector's model.

        Returns:
            str: Model identifier (e.g., "gpt", "claude", "gemini")
        """
        pass

    @abstractmethod
    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch a response from the LLM model.

        Args:
            query: The user's query or question
            context: Optional context information to augment the query

        Returns:
            Dict[str, Any]: Standardized response schema
                - model (str): Model identifier
                - response (str): Normalized text response
                - success (bool): Whether the call succeeded
                - error (Optional[str]): Error message if failed
                - latency_ms (int): Latency in milliseconds

        Raises:
            Exception: Implementations should catch all exceptions and
                       return them via the error field in the response dict.
                       This method should NEVER raise an exception.
        """
        pass
