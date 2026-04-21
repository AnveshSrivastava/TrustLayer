"""Core module for the hallucination detector.

This module exports the base collector interface and registry for use
throughout the system. It serves as the central point for collector
management and abstraction.

Exports:
    BaseCollector: Abstract base class for all collectors
    get_registry: Function to access the global collector registry
"""

from core.base_collector import BaseCollector
from core.registry import get_registry

__all__ = ["BaseCollector", "get_registry"]
