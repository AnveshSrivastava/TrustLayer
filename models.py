"""Pydantic models for the hallucination detector API.

This module defines the input and output schemas using Pydantic v2.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal


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


class AnalysisResponse(BaseModel):
    """Schema for analysis response."""

    query: str = Field(..., description="The original query")
    responses: Dict[str, Any] = Field(..., description="Analysis responses from different engines")
    status: str = Field(..., description="Status of the analysis")