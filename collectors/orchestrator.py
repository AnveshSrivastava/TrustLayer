"""Registry-based orchestrator for dynamic collector management.

This module implements the orchestration logic that fetches collectors
from the registry and executes them in parallel without knowing their
specific implementations or names upfront.

Key Design Principle:
    The orchestrator NEVER imports specific collectors or references
    model names. It is entirely driven by the registry, enabling true
    plug-and-play architecture.
"""

import asyncio
import datetime
from typing import Dict, Any, List, Optional

from core import get_registry


async def orchestrate_collection(
    query: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Orchestrate response collection from all registered collectors.

    This function:
    1. Fetches all collectors from the registry
    2. Executes them in parallel using asyncio.gather
    3. Normalizes and aggregates results
    4. Returns a structured response with metadata

    Args:
        query: The user's query to send to all models
        context: Optional context information

    Returns:
        Dict[str, Any]: Structured response containing:
            - query: The original query
            - responses: Dict mapping model names to their responses
            - status: High-level status (e.g., "success", "partial failure")
            - collection_metadata: Aggregated metrics about the collection

    Design Characteristics:
        - No hardcoded model names
        - Fully async/await compatible
        - Exception safe: failures in one collector don't affect others
        - Automatically scales with new collectors
    """
    registry = get_registry()
    collectors = registry.get_all()

    if not collectors:
        return _build_empty_response(query, "no collectors registered")

    # Create tasks for all collectors to execute in parallel
    tasks = [
        collector.get_response(query, context)
        for collector in collectors.values()
    ]

    # Execute all collectors in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and normalize exceptions
    normalized_responses: Dict[str, Dict[str, Any]] = {}
    for collector_id, (model_name, collector), result in zip(
        range(len(collectors)),
        collectors.items(),
        results
    ):
        if isinstance(result, Exception):
            # Handle exception from collector task
            normalized_responses[model_name] = {
                "model": model_name,
                "response": "",
                "success": False,
                "error": str(result).strip() or "Collector task failed",
                "latency_ms": 0,
            }
        elif isinstance(result, dict):
            # Ensure response conforms to schema
            normalized_responses[model_name] = _validate_response(model_name, result)
        else:
            # Unexpected response type
            normalized_responses[model_name] = {
                "model": model_name,
                "response": "",
                "success": False,
                "error": f"Invalid response type: {type(result).__name__}",
                "latency_ms": 0,
            }

    # Build metadata
    metadata = _build_metadata(normalized_responses)

    # Determine overall status
    status = _determine_status(metadata)

    return {
        "query": query,
        "responses": normalized_responses,
        "status": status,
        "collection_metadata": metadata,
    }


def _validate_response(model_name: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a response to the standard schema.

    Args:
        model_name: The model identifier
        response: The response from the collector

    Returns:
        Dict[str, Any]: Normalized response
    """
    return {
        "model": response.get("model", model_name),
        "response": str(response.get("response", "")) if response.get("response") is not None else "",
        "success": bool(response.get("success", False)),
        "error": response.get("error"),
        "latency_ms": int(response.get("latency_ms", 0)),
    }


def _build_metadata(responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build collection metadata from responses.

    Args:
        responses: Mapping of model names to responses

    Returns:
        Dict[str, Any]: Metadata including totals, averages, and timestamp
    """
    total_models = len(responses)
    successful_models = sum(
        1 for resp in responses.values() if resp.get("success", False)
    )
    failed_models = [
        name for name, resp in responses.items()
        if not resp.get("success", False)
    ]

    latencies = [
        resp.get("latency_ms", 0) for resp in responses.values()
    ]
    average_latency_ms = (
        float(sum(latencies)) / total_models
        if total_models > 0
        else 0.0
    )
    max_latency_ms = max(latencies) if latencies else 0

    return {
        "total_models": total_models,
        "successful_models": successful_models,
        "failed_models": failed_models,
        "average_latency_ms": average_latency_ms,
        "max_latency_ms": max_latency_ms,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def _determine_status(metadata: Dict[str, Any]) -> str:
    """Determine the overall status based on metadata.

    Args:
        metadata: Collection metadata

    Returns:
        str: Status string
    """
    total = metadata.get("total_models", 0)
    successful = metadata.get("successful_models", 0)

    if successful == total and total > 0:
        return "success"
    elif successful > 0:
        return "partial failure"
    elif total == 0:
        return "no collectors"
    else:
        return "failure"


def _build_empty_response(query: str, reason: str) -> Dict[str, Any]:
    """Build an empty response when no collectors are available.

    Args:
        query: The original query
        reason: Reason for empty response

    Returns:
        Dict[str, Any]: Empty response with metadata
    """
    return {
        "query": query,
        "responses": {},
        "status": reason,
        "collection_metadata": {
            "total_models": 0,
            "successful_models": 0,
            "failed_models": [],
            "average_latency_ms": 0.0,
            "max_latency_ms": 0,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    }
