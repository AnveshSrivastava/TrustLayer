"""FastAPI application entry point for the hallucination detector.

This module defines the main FastAPI application with routes and orchestration.
It orchestrates both the collection phase (parallel LLM queries) and the analysis
phase (semantic analysis, contradiction detection, similarity scoring).

Architecture:
1. Startup Phase: Eagerly load all analyzer models to avoid cold starts
2. Collection Phase: Parallel async calls to all registered collectors
3. Analysis Phase: Sequential synchronous calls to all registered analyzers
4. Response Phase: Merged results with both collection and analysis metadata

Design Principle:
- No business logic in routes
- No hardcoded model names or analyzer names
- Clean separation of concerns
- Production-grade reliability with execution tracking
"""

import logging

from fastapi import FastAPI

# Import collectors to trigger auto-registration
from collectors import gpt, groq, gemini

from collectors.collector import collect_responses
from analyzers.analyzer import run_analyzers
from models import QueryInput, AnalysisResponse

logger = logging.getLogger("hallucination_detector")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Hallucination Detector API",
    description="API for detecting hallucinations in AI responses",
    version="1.0.0"
)


# ============================================================================
# STARTUP & SHUTDOWN HOOKS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Eagerly load analyzer models during application startup.
    
    This ensures:
    - All models are loaded into memory before requests arrive
    - No cold starts on the first request
    - Failures during model loading are caught early (fail fast)
    
    Timing:
    - Runs once when application starts
    - Completes before first request arrives
    - If STRICT_MODE is True, any failure prevents app startup
    - If STRICT_MODE is False, app starts even if some analyzers fail
    """
    logger.info("=" * 70)
    logger.info("STARTUP: Warming up analyzer models...")
    logger.info("=" * 70)
    
    try:
        from analyzers.registry import warmup_analyzers
        warmup_analyzers()
        logger.info("✓ Startup complete: All analyzers ready")
    except Exception as exc:
        logger.error(f"✗ Startup failed: {str(exc)}", exc_info=True)
        raise


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/")
def root() -> dict:
    """Root endpoint returning API information."""
    return {"name": "Hallucination Detector API", "version": "1.0.0"}


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(query: QueryInput) -> AnalysisResponse:
    """Analyze a query by collecting responses and running semantic analysis.

    This endpoint orchestrates the complete hallucination detection pipeline:

    1. COLLECTION PHASE (Parallel):
       - Receives the query and optional context
       - Calls collect_responses() from the collector orchestrator
       - All registered collectors execute in parallel (async)
       - Each collector returns: {model, response, success, error, latency_ms}
       - Aggregate metadata: total, successful, failed, latencies, timestamp

    2. ANALYSIS PHASE (Sequential):
       - Calls run_analyzers() with collected responses and context
       - All registered analyzers run sequentially (sync, CPU-bound)
       - Each analyzer returns: {analyzer_name, success, error, ...analyzer-specific...}
       - Aggregate metadata: total, successful, failed analyzers, timestamp

    3. RESPONSE PHASE:
       - Merges collection results + analysis results
       - Returns unified AnalysisResponse with all metadata

    Args:
        query: QueryInput containing:
               - query (required): The query to analyze
               - context (optional): Background context
               - expected_answer (optional): Known correct answer
               - query_type (optional): "factual", "reasoning", "opinion", "open_ended"
               - metadata (optional): Custom metadata dict

    Returns:
        AnalysisResponse: Complete response with:
                - query: Original query
                - responses: Per-model responses with latencies
                - status: "success" or "failed"
                - collection_metadata: Aggregated collection stats
                - analysis: Per-analyzer analysis results
                - analysis_metadata: Aggregated analysis stats

    Design Notes:
    - Collection phase is async (parallel I/O to APIs)
    - Analysis phase is sync (CPU-bound NLI, embeddings)
    - No model names or analyzer names hardcoded
    - Fully dynamic based on registries
    - Scales to any number of models or analyzers
    """
    logger.info("Received analyze request for query: %s", query.query)

    try:
        # ===================================================================
        # PHASE 1: COLLECTION (Parallel async)
        # ===================================================================
        collection_result = await collect_responses(query.query, query.context)

        # ===================================================================
        # PHASE 2: ANALYSIS (Sequential sync)
        # ===================================================================
        # Extract responses dict for analyzers
        responses_for_analysis = collection_result.get("responses", {})

        # Run all registered analyzers
        analysis_result = run_analyzers(responses_for_analysis, query.context)

        # ===================================================================
        # PHASE 3: MERGE RESULTS
        # ===================================================================
        merged_result = {
            "query": query.query,
            "responses": collection_result.get("responses", {}),
            "status": collection_result.get("status", "unknown"),
            "collection_metadata": collection_result.get("metadata", {}),
            "analysis": analysis_result.get("analysis", {}),
            "analysis_metadata": analysis_result.get("analysis_metadata", {}),
        }

        logger.info(
            "Completed analyze request for query: %s with status: %s",
            query.query,
            merged_result.get("status"),
        )

        return AnalysisResponse(**merged_result)

    except Exception as exc:
        logger.error("Error during analysis: %s", str(exc), exc_info=True)

        # Return error response
        error_response = {
            "query": query.query,
            "responses": {},
            "status": "error",
            "collection_metadata": {
                "total_models": 0,
                "successful_models": 0,
                "failed_models": [],
                "average_latency_ms": 0.0,
                "max_latency_ms": 0,
                "timestamp": "",
            },
            "analysis": {},
            "analysis_metadata": {
                "total_analyzers": 0,
                "successful_analyzers": 0,
                "failed_analyzers": [],
                "timestamp": "",
            },
        }

        return AnalysisResponse(**error_response)