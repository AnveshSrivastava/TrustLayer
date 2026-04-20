"""Collector orchestrator for the hallucination detector.

This module aggregates responses from all configured model collectors.
"""

import asyncio
import datetime
from typing import Optional, Dict, Any, List

from collectors import claude, gpt, gemini


def _normalize_response(model_name: str, payload: Any) -> Dict[str, Any]:
    """Normalize any collector result or exception into the strict schema."""
    if isinstance(payload, Exception):
        return {
            "model": model_name,
            "response": "",
            "success": False,
            "error": str(payload).strip() or "Collector exception",
            "latency_ms": 0,
        }

    if not isinstance(payload, dict):
        return {
            "model": model_name,
            "response": "",
            "success": False,
            "error": "Invalid collector response format",
            "latency_ms": 0,
        }

    return {
        "model": payload.get("model", model_name),
        "response": str(payload.get("response", "")) if payload.get("response") is not None else "",
        "success": bool(payload.get("success", False)),
        "error": payload.get("error"),
        "latency_ms": int(payload.get("latency_ms", 0)),
    }


def _build_metadata(responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build collection metadata for the aggregator response."""
    total_models = len(responses)
    successful_models = sum(1 for value in responses.values() if value.get("success", False))
    failed_models = [name for name, value in responses.items() if not value.get("success", False)]
    latencies = [value.get("latency_ms", 0) for value in responses.values()]
    average_latency_ms = float(sum(latencies)) / total_models if total_models else 0.0
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
    """Collect responses from all configured model collectors in parallel."""
    tasks = [
        ("claude", claude.get_response(query, context)),
        ("gpt", gpt.get_response(query, context)),
        ("gemini", gemini.get_response(query, context)),
    ]
    coroutines = [task for _, task in tasks]
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    normalized_responses: Dict[str, Dict[str, Any]] = {}
    for (model_name, _), result in zip(tasks, results):
        normalized = _normalize_response(model_name, result)
        normalized_responses[model_name] = normalized

    metadata = _build_metadata(normalized_responses)
    status = "completed" if metadata["successful_models"] == metadata["total_models"] else "partial failure"

    return {
        "query": query,
        "responses": normalized_responses,
        "status": status,
        "collection_metadata": metadata,
    }