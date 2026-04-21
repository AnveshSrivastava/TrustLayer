"""Utility functions for the analyzers module.

Provides lightweight text processing and data handling utilities.
"""

import re
from typing import Optional


def normalize_text(text: str) -> str:
    """Normalize text for semantic analysis.

    Performs the following operations:
    1. Convert to lowercase
    2. Strip leading/trailing whitespace
    3. Collapse multiple consecutive spaces to single space
    4. Remove trivial punctuation inconsistencies

    Args:
        text: Input text to normalize

    Returns:
        Normalized text string

    Examples:
        >>> normalize_text("  Hello    WORLD  ")
        "hello world"
        >>> normalize_text("What  is  AI?")
        "what is ai"
        >>> normalize_text("Machine  Learning!!!")
        "machine learning"
    """
    if not isinstance(text, str):
        return ""

    # Convert to lowercase
    text = text.lower()

    # Strip leading/trailing whitespace
    text = text.strip()

    # Collapse multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)

    # Remove trivial punctuation inconsistencies
    # Keep only alphanumeric, spaces, and essential punctuation (. , ? ! : ; - )
    text = re.sub(r'[^\w\s\.\,\?\!\:\;\-]', '', text)

    # Clean up any double punctuation or trailing punctuation
    text = re.sub(r'[\.\,\?\!\:\;\-]+', lambda m: m.group(0)[0], text)

    return text.strip()
