"""Analyzer orchestrator for the hallucination detector.

This module coordinates the execution of all registered analyzers.
It runs analyzers sequentially and aggregates results into a unified response.

Analyzers are LAZY-LOADED to avoid import-time model loading issues.
They are instantiated only when actually needed (during analysis).

EXECUTION TRACKING:
===================
Each analyzer's execution is tracked for observability:
- start_time: time.monotonic() before analysis
- end_time: time.monotonic() after analysis  
- execution_time_ms: (end - start) * 1000, rounded to int

This timing is recorded for BOTH success and failure cases.

Key Design Principle:
- This module NEVER references specific analyzer names
- All analyzer discovery is dynamic via ACTIVE_ANALYZER_CLASSES registry
- Fully scalable to any number of analyzers without code changes
- Failures are isolated per analyzer (one failure doesn't crash others)
"""

import datetime
import time
from typing import Optional, Dict, Any

from analyzers.registry import ACTIVE_ANALYZER_CLASSES


def run_analyzers(
    responses: Dict[str, Dict[str, Any]],
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Run all registered analyzers on the collected responses.

    Executes analyzers sequentially and collects results. Each analyzer
    receives the same responses dict and optional context, allowing it to
    compute independent analysis.

    Analyzers are instantiated lazily only when this function is called,
    avoiding model loading at import time.

    Execution Tracking:
    - Records execution_time_ms for each analyzer
    - Tracks execution time for both success and failure cases
    - Aggregates total execution time across all analyzers

    Args:
        responses: Dict mapping model names to response dicts
        context: Optional context string from the original query

    Returns:
        Dict[str, Any]: Aggregated analysis results

        Returns:
        {
            "analysis": {
                "<analyzer_name>": {
                    ...analyzer result...,
                    "execution_time_ms": int
                },
                ...
            },
            "analysis_metadata": {
                "total_analyzers": int,
                "successful_analyzers": int,
                "failed_analyzers": list[str],
                "total_execution_time_ms": int,
                "timestamp": str (ISO UTC)
            }
        }

    Design Notes:
        - No analyzer names hardcoded
        - Works for N analyzers without modification
        - Each analyzer failure is isolated (doesn't affect others)
        - Timestamps track when analysis completed
        - Execution time includes instantiation + analysis
        - Analyzers are instantiated lazily (only when this function runs)
    """
    analysis_results: Dict[str, Dict[str, Any]] = {}
    failed_analyzers: list[str] = []
    successful_count = 0
    total_execution_time_ms = 0

    # Track overall orchestration time
    orchestration_start = time.monotonic()

    # Run each analyzer sequentially
    for analyzer_class in ACTIVE_ANALYZER_CLASSES:
        analyzer_start = time.monotonic()
        analyzer_name = "unknown"

        try:
            # Instantiate analyzer lazily
            analyzer = analyzer_class()
            analyzer_name = getattr(analyzer, 'analyzer_name', analyzer_class.__name__)

            # Call analyzer and record execution time
            result = analyzer.analyze(responses, context)

            # Compute execution time (includes instantiation + analysis)
            analyzer_end = time.monotonic()
            execution_time_ms = int((analyzer_end - analyzer_start) * 1000)

            # Inject execution time into result
            result["execution_time_ms"] = execution_time_ms
            total_execution_time_ms += execution_time_ms

            # Store result
            analysis_results[analyzer_name] = result

            # Track success
            if result.get("success", False):
                successful_count += 1
            else:
                failed_analyzers.append(analyzer_name)

        except Exception as exc:
            # Compute execution time even on failure
            analyzer_end = time.monotonic()
            execution_time_ms = int((analyzer_end - analyzer_start) * 1000)
            total_execution_time_ms += execution_time_ms

            # Catch any unexpected exceptions
            failed_analyzers.append(analyzer_name)

            analysis_results[analyzer_name] = {
                "analyzer_name": analyzer_name,
                "success": False,
                "error": f"Orchestrator caught exception during instantiation or analysis: {str(exc)}",
                "execution_time_ms": execution_time_ms,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

    # Compute orchestration time
    orchestration_end = time.monotonic()
    orchestration_time_ms = int((orchestration_end - orchestration_start) * 1000)

    # Build metadata
    analysis_metadata = {
        "total_analyzers": len(ACTIVE_ANALYZER_CLASSES),
        "successful_analyzers": successful_count,
        "failed_analyzers": failed_analyzers,
        "total_execution_time_ms": orchestration_time_ms,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    return {
        "analysis": analysis_results,
        "analysis_metadata": analysis_metadata,
    }
