"""Base abstract class for all analyzers in the hallucination detector.

This module defines the contract that all analyzers must follow.
Analyzers are synchronous, CPU-bound components that process collected responses
and provide semantic analysis, contradiction detection, and similarity scoring.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseAnalyzer(ABC):
    """Abstract base class for all analyzers.

    All analyzers must inherit from this class and implement the analyze() method.
    Analyzers are synchronous (CPU-bound) and must follow the strict response contract.

    Attributes:
        analyzer_name (str): Unique identifier for this analyzer (e.g., "semantic_similarity")
    """

    analyzer_name: str

    @abstractmethod
    def analyze(
        self,
        responses: Dict[str, Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze collected responses for hallucinations or semantic patterns.

        This method must be implemented by all concrete analyzers.

        Args:
            responses: Dictionary mapping model names to their response dicts.
                      Each response dict should contain: {model, response, success, error, latency_ms}
            context: Optional context string for the original query

        Returns:
            Dict[str, Any]: Structured analysis result with strict contract:
                {
                    "analyzer_name": str,                # Name of this analyzer
                    "success": bool,                     # Whether analysis succeeded
                    "error": Optional[str],              # Error message if failed
                    ... (analyzer-specific fields)       # Additional analysis results
                }

        Contract Guarantees:
            - Always returns a dict (never raises exceptions)
            - Always includes: analyzer_name, success, error
            - Always catches exceptions and returns normalized error dict
            - error field is None if success=True
            - error field is string if success=False

        Examples:
            >>> analyzer = MyAnalyzer()
            >>> responses = {
            ...     "gpt": {"model": "gpt", "response": "Yes", "success": True, ...},
            ...     "gemini": {"model": "gemini", "response": "No", "success": True, ...}
            ... }
            >>> result = analyzer.analyze(responses)
            >>> result["analyzer_name"]
            "my_analyzer"
            >>> result["success"]
            True
        """
        pass
