"""Parallel orchestrator for collecting responses from all registered collectors.

This module:
1. Fetches collectors from the registry (collectors/registry.py)
2. Executes all collectors in parallel using asyncio.gather()
3. Handles exceptions gracefully (one failure doesn't crash system)
4. Normalizes all responses to the standard schema
5. Computes collection metadata (latency, success rate, etc.)

Key Design Principle:
- This module NEVER references specific model names
- All collector discovery is dynamic via ACTIVE_COLLECTORS registry
- Fully scalable to any number of models without code changes
"""

import asyncio
import datetime
from typing import Optional, Dict, Any

from collectors.registry import ACTIVE_COLLECTORS


def _normalize_response(model_name: str, payload: Any) -> Dict[str, Any]:
    """Normalize any collector result or exception into the strict schema.

    Args:
        model_name: The model identifier
        payload: Either a dict (response) or Exception

    Returns:
        Dict[str, Any]: Normalized response matching the schema:
            {
                "model": str,
                "response": str,
                "success": bool,
                "error": Optional[str],
                "latency_ms": int
            }
    """
    # Handle exception from asyncio.gather
    if isinstance(payload, Exception):
        return {
            "model": model_name,
            "response": "",
            "success": False,
            "error": str(payload).strip() or "Collector exception",
            "latency_ms": 0,
        }

    # Handle invalid response type
    if not isinstance(payload, dict):
        return {
            "model": model_name,
            "response": "",
            "success": False,
            "error": f"Invalid response type: {type(payload).__name__}",
            "latency_ms": 0,
        }

    # Normalize valid response dict
    return {
        "model": payload.get("model", model_name),
        "response": str(payload.get("response", "")) if payload.get("response") is not None else "",
        "success": bool(payload.get("success", False)),
        "error": payload.get("error"),
        "latency_ms": int(payload.get("latency_ms", 0)),
    }


def _build_metadata(responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build collection metadata from all responses.

    Computes:
    - Total models queried
    - Number of successful responses
    - List of failed models
    - Average latency across all models
    - Maximum latency observed
    - ISO UTC timestamp

    Args:
        responses: Dict mapping model names to their responses

    Returns:
        Dict[str, Any]: Metadata dictionary
    """
    total_models = len(responses)
    successful_models = sum(1 for resp in responses.values() if resp.get("success", False))
    failed_models = [
        name for name, resp in responses.items()
        if not resp.get("success", False)
    ]

    latencies = [resp.get("latency_ms", 0) for resp in responses.values()]
    average_latency_ms = float(sum(latencies)) / total_models if total_models > 0 else 0.0
    max_latency_ms = max(latencies) if latencies else 0

    return {
        "total_models": total_models,
        "successful_models": successful_models,
        "failed_models": failed_models,
        "average_latency_ms": average_latency_ms,
        "max_latency_ms": max_latency_ms,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


async def collect_responses(query: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Collect responses from all registered collectors in parallel.

    This function:
    1. Gets all collectors from ACTIVE_COLLECTORS registry
    2. Creates async tasks for each collector
    3. Executes all in parallel with asyncio.gather()
    4. Handles exceptions gracefully
    5. Normalizes all responses
    6. Builds metadata
    7. Returns structured response

    Args:
        query: The user's query/question
        context: Optional context information

    Returns:
        Dict[str, Any]: Structured response
            {
                "query": str,
                "responses": {
                    "<model_name>": {normalized_response}
                },
                "status": str,
                "collection_metadata": {...}
            }

    Key Features:
    - Fully dynamic: works with any number of collectors
    - Exception safe: one collector failure doesn't affect others
    - No model name hardcoding
    - Scales to unlimited models
    """
    # Get all registered collectors from registry
    collectors = ACTIVE_COLLECTORS

    if not collectors:
        # No collectors registered, return empty response
        return {
            "query": query,
            "responses": {},
            "status": "no collectors registered",
            "collection_metadata": {
                "total_models": 0,
                "successful_models": 0,
                "failed_models": [],
                "average_latency_ms": 0.0,
                "max_latency_ms": 0,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        }

    # Create async tasks for each collector
    tasks = [collector.get_response(query, context) for collector in collectors]

    # Execute all collectors in parallel
    # return_exceptions=True ensures one failure doesn't crash entire gather
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Normalize responses and map to model names
    normalized_responses: Dict[str, Dict[str, Any]] = {}
    for collector, result in zip(collectors, results):
        model_name = collector.model_name
        normalized = _normalize_response(model_name, result)
        normalized_responses[model_name] = normalized

    # Build metadata
    metadata = _build_metadata(normalized_responses)

    # Determine overall status
    if metadata["successful_models"] == metadata["total_models"] and metadata["total_models"] > 0:
        status = "success"
    elif metadata["successful_models"] > 0:
        status = "partial failure"
    elif metadata["total_models"] > 0:
        status = "failure"
    else:
        status = "no models"

    return {
        "query": query,
        "responses": normalized_responses,
        "status": status,
        "collection_metadata": metadata,
    }