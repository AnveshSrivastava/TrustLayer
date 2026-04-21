"""Analyzer registry for the hallucination detector.

CRITICAL DESIGN PRINCIPLE:
===========================

This file is the ONLY place where analyzers should be registered.
Do NOT import analyzers directly anywhere else in the codebase.
Always use ACTIVE_ANALYZER_CLASSES from this module.

Analyzers are LAZY-LOADED to avoid import-time model loading issues.
They are instantiated only when actually needed (during analysis).

STRICT MODE BEHAVIOR:
====================

STRICT_MODE = True  → Analyzer failures raise exceptions (fail fast, good for research)
STRICT_MODE = False → Analyzer failures print warnings (graceful degradation, production)

To add a new analyzer:
1. Create analyzer in analyzers/my_analyzer.py
2. Import: from analyzers.my_analyzer import MyAnalyzer
3. Add to ACTIVE_ANALYZER_CLASSES: MyAnalyzer

That's it! No other changes needed.
"""

import datetime
from typing import List, Type

from analyzers.base import BaseAnalyzer

# ============================================================================
# STRICT MODE CONFIGURATION
# ============================================================================

# If True: Analyzer failures raise exceptions and stop execution
# If False: Analyzer failures print warnings and continue
STRICT_MODE = False

"""
STRICT_MODE Rationale:
- Set to True for research/development (fail fast on issues)
- Set to False for production (graceful degradation)
- Affects both registry initialization and warmup
"""

# Registry of analyzer CLASSES (not instances) for lazy loading
ACTIVE_ANALYZER_CLASSES: List[Type[BaseAnalyzer]] = []


def _initialize_analyzers():
    """Lazy initialization of analyzer classes.
    
    This function is called once to populate the registry.
    Models are loaded only when analyzers are instantiated during analysis.
    
    STRICT_MODE behavior:
    - True: Any import failure raises exception
    - False: Failures print warnings and skip analyzer
    """
    global ACTIVE_ANALYZER_CLASSES

    if ACTIVE_ANALYZER_CLASSES:
        # Already initialized
        return

    # Attempt to load SimilarityAnalyzer
    try:
        from analyzers.similarity import SimilarityAnalyzer
        ACTIVE_ANALYZER_CLASSES.append(SimilarityAnalyzer)
    except Exception as exc:
        error_msg = f"Could not load SimilarityAnalyzer: {str(exc)}"
        if STRICT_MODE:
            raise RuntimeError(error_msg)
        else:
            print(f"Warning: {error_msg}")

    # Attempt to load NLIAnalyzer
    try:
        from analyzers.nli import NLIAnalyzer
        ACTIVE_ANALYZER_CLASSES.append(NLIAnalyzer)
    except Exception as exc:
        error_msg = f"Could not load NLIAnalyzer: {str(exc)}"
        if STRICT_MODE:
            raise RuntimeError(error_msg)
        else:
            print(f"Warning: {error_msg}")


def warmup_analyzers() -> None:
    """Eagerly instantiate all registered analyzers to force model loading.
    
    This function should be called during application startup to avoid
    cold starts during the first request. It forces all models to load
    into memory before any requests arrive.
    
    STRICT_MODE behavior:
    - True: Any instantiation failure raises exception (fail fast)
    - False: Failures print warnings and continue (graceful degradation)
    
    Returns:
        None
        
    Raises:
        RuntimeError: If STRICT_MODE is True and any analyzer fails to instantiate
        
    Side Effects:
        - Loads all analyzer models into memory
        - Prints warnings for any analyzers that fail to load
    
    Example:
        >>> warmup_analyzers()
        >>> # All models now loaded, no cold starts on first request
    """
    _initialize_analyzers()
    
    for analyzer_class in ACTIVE_ANALYZER_CLASSES:
        try:
            # Instantiate analyzer to force model loading
            analyzer = analyzer_class()
            print(f"✓ Warmup: {analyzer_class.__name__} loaded successfully")
        except Exception as exc:
            error_msg = f"Warmup failed for {analyzer_class.__name__}: {str(exc)}"
            if STRICT_MODE:
                raise RuntimeError(error_msg)
            else:
                print(f"Warning: {error_msg}")


# Initialize on first import
_initialize_analyzers()

"""
CRITICAL NOTE:
- This list contains analyzer CLASSES, not instances
- Instances are created lazily when analyzers are used
- Each analyzer must implement BaseCollector contract
- Adding a new analyzer requires only adding one class to ACTIVE_ANALYZER_CLASSES

Do NOT:
- Import analyzers directly elsewhere in the codebase
- Reference analyzer names as strings (e.g., "semantic_similarity") outside this file
- Create multiple instances of analyzers (use singleton pattern)
- Modify this registry at runtime after initialization
"""
