"""Centralized configuration management for the hallucination detector.

This module loads environment variables using python-dotenv and validates
required API keys. It exports the keys as module-level constants for easy access.
"""

from dotenv import load_dotenv
import os
from typing import Dict

# Load environment variables from .env file
load_dotenv()


def load_config() -> Dict[str, str]:
    """Load and validate required environment variables.

    Raises:
        ValueError: If any required environment variable is missing or empty.
    """
    required_keys = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY', 'GROQ_API_KEY']
    config: Dict[str, str] = {}

    for key in required_keys:
        value = os.getenv(key)
        if not value or value.strip() == '':
            raise ValueError(f"Missing or empty environment variable: {key}")
        config[key] = value

    return config


# Load configuration at import time
_config = load_config()

# Export API keys as module-level constants
ANTHROPIC_API_KEY: str = _config['ANTHROPIC_API_KEY']
OPENAI_API_KEY: str = _config['OPENAI_API_KEY']
GEMINI_API_KEY: str = _config['GEMINI_API_KEY']
GROQ_API_KEY: str = _config['GROQ_API_KEY']