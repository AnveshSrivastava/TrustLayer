"""FastAPI application entry point for the hallucination detector.

This module defines the main FastAPI application with routes and orchestration.
It calls the orchestrator which dynamically fetches collectors from the registry.

Design Principle:
- No business logic in routes
- No hardcoded model names
- Clean separation of concerns
"""

import logging

from fastapi import FastAPI

# Import collectors to trigger auto-registration
from collectors import gpt, groq, gemini

from collectors.collector import collect_responses
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

    This endpoint:
    1. Receives a query and optional context
    2. Calls collect_responses() from the orchestrator
    3. The orchestrator fetches all collectors from the registry
    4. All collectors execute in parallel
    5. Responses are normalized and aggregated
    6. Returns structured response with metadata

    Args:
        query: QueryInput containing the query and optional context

    Returns:
        AnalysisResponse: Responses from all models with metadata

    Design Notes:
    - No model names referenced in this route
    - Fully dynamic based on registry
    - Scales to any number of models
    """
    logger.info("Received analyze request for query: %s", query.query)
    result = await collect_responses(query.query, query.context)
    logger.info(
        "Completed analyze request for query: %s with status: %s",
        query.query,
        result.get("status"),
    )
    return AnalysisResponse(**result)