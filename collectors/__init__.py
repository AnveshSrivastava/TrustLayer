"""Hallucination detector collectors package.

This package contains modules for collecting data and responses from various sources.

All collector modules are imported here to trigger auto-registration with the global
registry when the package is imported. This ensures that all collectors are available
through the registry without requiring explicit knowledge of specific collector modules.
"""

# Import collectors to trigger auto-registration
from collectors import gpt, claude, gemini

__all__ = ["gpt", "claude", "gemini"]