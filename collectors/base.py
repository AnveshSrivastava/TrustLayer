"""Base collector interface for the hallucination detector.

This module defines the abstract base class that all collectors must inherit from.
It enforces a strict contract ensuring all collectors return standardized responses.

All collectors must implement:
- model_name: str (class-level or property)
- get_response(query: str, context: Optional[str]) -> dict

Return Contract (STRICT):
{
    "model": str,              # Model identifier
    "response": str,           # Text response
    "success": bool,           # Whether call succeeded
    "error": Optional[str],    # Error message if failed
    "latency_ms": int          # Latency in milliseconds
}

This contract is MANDATORY. No deviations allowed.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseCollector(ABC):
    """Abstract base class for all LLM collectors.

    All collectors must:
    1. Inherit from BaseCollector
    2. Define model_name property
    3. Implement get_response() async method
    4. Return standardized response schema

    This ensures loose coupling and enables the system to work with
    any number of LLM models without hardcoding model names.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the unique identifier for this collector's model.

        Examples: "gpt", "claude", "gemini", "llama"

        Returns:
            str: Model identifier
        """
        pass

    @abstractmethod
    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch a response from the LLM model.

        This method MUST:
        - Handle timeouts (10 seconds)
        - Implement retry logic (1 retry)
        - Measure latency
        - Never raise exceptions
        - Always return the standardized schema

        Args:
            query: The user's query or question
            context: Optional context information to augment the query

        Returns:
            Dict[str, Any]: Standardized response schema
                {
                    "model": str,              # Model identifier
                    "response": str,           # Text response
                    "success": bool,           # Success indicator
                    "error": Optional[str],    # Error message if failed
                    "latency_ms": int          # Latency in milliseconds
                }

        Raises:
            Nothing. This method must catch all exceptions and
            return them in the response schema via the error field.
            Never let exceptions propagate.
        """
        pass
