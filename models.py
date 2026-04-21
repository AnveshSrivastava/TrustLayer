"""Pydantic models for the hallucination detector API.

This module defines the input and output schemas using Pydantic v2.
"""

from typing import Optional, Dict, Any, Literal, List

from pydantic import BaseModel, Field


class QueryInput(BaseModel):
    """Schema for input query to analyze for hallucinations."""

    query: str = Field(..., description="The query text to analyze")
    context: Optional[str] = Field(None, description="Optional context information")
    expected_answer: Optional[str] = Field(None, description="Expected answer for comparison")
    query_type: Literal["factual", "reasoning", "opinion", "open_ended"] = Field(
        "factual", description="Type of query"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModelResponse(BaseModel):
    """Schema for a single model response."""

    model: str = Field(..., description="Model identifier")
    response: str = Field(..., description="Normalized text response")
    success: bool = Field(..., description="Whether the model call succeeded")
    error: Optional[str] = Field(None, description="Error message if the model call failed")
    latency_ms: int = Field(..., description="Latency in milliseconds")


class CollectionMetadata(BaseModel):
    """Schema for collection metadata aggregated across models."""

    total_models: int = Field(..., description="Total number of models queried")
    successful_models: int = Field(..., description="Number of successful model responses")
    failed_models: List[str] = Field(..., description="List of model names that failed")
    average_latency_ms: float = Field(..., description="Average latency across all models")
    max_latency_ms: int = Field(..., description="Maximum latency observed")
    timestamp: str = Field(..., description="ISO UTC timestamp of the collection")


class AnalysisResponse(BaseModel):
    """Schema for the analysis response returned by the API."""

    query: str = Field(..., description="The original query")
    responses: Dict[str, ModelResponse] = Field(..., description="Responses from each model")
    status: str = Field(..., description="High-level status of the collection")
    collection_metadata: CollectionMetadata = Field(..., description="Metadata for the collection process")
    analysis: Dict[str, Any] = Field(default_factory=dict, description="Analysis results from all analyzers")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata for the analysis process")