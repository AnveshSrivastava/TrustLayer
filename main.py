"""FastAPI application entry point for the hallucination detector.

This module defines the main FastAPI application with routes and orchestration.
It uses the registry-based orchestrator to collect responses from all registered
models without hardcoding specific collector implementations.
"""

import logging

from fastapi import FastAPI

# Import collectors to trigger auto-registration
from collectors import gpt, claude, gemini
from collectors.orchestrator import orchestrate_collection
from models import QueryInput, AnalysisResponse

logger = logging.getLogger("hallucination_detector")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Hallucination Detector API",
    description="API for detecting hallucinations in AI responses",
    version="1.0.0"
)


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
    """Analyze a query by collecting responses from all registered models.

    This endpoint uses the registry-based orchestrator which automatically
    discovers and invokes all registered collectors without hardcoding
    specific model names or implementations.

    Args:
        query: QueryInput containing the query and optional context

    Returns:
        AnalysisResponse: Responses from all models with metadata
    """
    logger.info("Received analyze request for query: %s", query.query)
    result = await orchestrate_collection(query.query, query.context)
    logger.info(
        "Completed analyze request for query: %s with status: %s",
        query.query,
        result.get("status"),
    )
    return AnalysisResponse(**result)