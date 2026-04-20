"""FastAPI application entry point for the hallucination detector.

This module defines the main FastAPI application with basic routes.
"""

from fastapi import FastAPI
from models import QueryInput, AnalysisResponse

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
def analyze(query: QueryInput) -> AnalysisResponse:
    """Analyze a query for potential hallucinations."""
    return AnalysisResponse(
        query=query.query,
        responses={},
        status="pipeline not connected"
    )