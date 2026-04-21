"""Collector registry for dynamic model management.

This module implements a registry pattern that enables dynamic registration
and discovery of collectors without hardcoding dependencies.

Key design principle: The orchestrator must NEVER import specific collectors.
Instead, it queries the registry at runtime. This enables true plug-and-play
architecture where new models can be added without touching core logic.
"""

from typing import Dict, List
from threading import RLock
from core.base_collector import BaseCollector


class CollectorRegistry:
    """Thread-safe registry for dynamic collector management.

    This registry maintains a mapping of model names to collector instances.
    It provides methods to register new collectors and retrieve all registered
    collectors at runtime without hardcoded dependencies.

    Thread Safety:
        All operations are protected by a reentrant lock to support
        concurrent registration and queries.
    """

    def __init__(self) -> None:
        """Initialize the registry with an empty collector map."""
        self._collectors: Dict[str, BaseCollector] = {}
        self._lock = RLock()

    def register(self, collector: BaseCollector) -> None:
        """Register a collector instance.

        Args:
            collector: An instance of BaseCollector (or subclass)

        Raises:
            TypeError: If collector does not inherit from BaseCollector
            ValueError: If a collector with the same model_name is already registered

        Thread Safe: Yes
        """
        if not isinstance(collector, BaseCollector):
            raise TypeError(
                f"Collector must inherit from BaseCollector, got {type(collector).__name__}"
            )

        with self._lock:
            model_name = collector.model_name
            if model_name in self._collectors:
                raise ValueError(
                    f"Collector for model '{model_name}' is already registered"
                )
            self._collectors[model_name] = collector

    def get_all(self) -> Dict[str, BaseCollector]:
        """Get all registered collectors.

        Returns:
            Dict[str, BaseCollector]: Mapping of model names to collector instances

        Thread Safe: Yes
        """
        with self._lock:
            return dict(self._collectors)

    def get(self, model_name: str) -> BaseCollector:
        """Retrieve a specific collector by model name.

        Args:
            model_name: The model identifier

        Returns:
            BaseCollector: The collector instance

        Raises:
            KeyError: If no collector is registered for the given model name

        Thread Safe: Yes
        """
        with self._lock:
            if model_name not in self._collectors:
                raise KeyError(
                    f"No collector registered for model '{model_name}'. "
                    f"Available models: {list(self._collectors.keys())}"
                )
            return self._collectors[model_name]

    def unregister(self, model_name: str) -> None:
        """Unregister a collector by model name.

        Args:
            model_name: The model identifier to remove

        Raises:
            KeyError: If no collector is registered for the given model name

        Thread Safe: Yes
        """
        with self._lock:
            if model_name not in self._collectors:
                raise KeyError(f"No collector registered for model '{model_name}'")
            del self._collectors[model_name]

    def is_registered(self, model_name: str) -> bool:
        """Check if a model is registered.

        Args:
            model_name: The model identifier

        Returns:
            bool: True if registered, False otherwise

        Thread Safe: Yes
        """
        with self._lock:
            return model_name in self._collectors

    def list_models(self) -> List[str]:
        """Get a list of all registered model names.

        Returns:
            List[str]: List of model identifiers

        Thread Safe: Yes
        """
        with self._lock:
            return list(self._collectors.keys())


# Global singleton registry instance
_global_registry = CollectorRegistry()


def get_registry() -> CollectorRegistry:
    """Get the global collector registry instance.

    Returns:
        CollectorRegistry: The singleton registry

    This function provides access to the global registry without
    requiring imports of internal structures.
    """
    return _global_registry
