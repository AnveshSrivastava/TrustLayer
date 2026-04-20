"""FastAPI application entry point for the hallucination detector.

This module defines the main FastAPI application with routes and orchestration.
"""

import logging

from fastapi import FastAPI

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
    """Analyze a query by collecting responses from multiple models."""
    logger.info("Received analyze request for query: %s", query.query)
    result = await collect_responses(query.query, query.context)
    logger.info(
        "Completed analyze request for query: %s with status: %s",
        query.query,
        result.get("status"),
    )
    return AnalysisResponse(**result)