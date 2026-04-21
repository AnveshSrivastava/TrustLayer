"""Collector registry for the hallucination detector.

CRITICAL DESIGN PRINCIPLE:
===========================

This file is the ONLY place where collectors should be registered.
Do NOT import collectors directly anywhere else in the codebase.
Always use ACTIVE_COLLECTORS from this module.

To add a new model:
1. Create collector in collectors/my_model.py
2. Import: from collectors.my_model import MyModelCollector
3. Add to ACTIVE_COLLECTORS: MyModelCollector()

That's it! No other changes needed.
"""

from collectors.gpt import GPTCollector
from collectors.groq import GroqCollector
from collectors.gemini import GeminiCollector


# ============================================================================
# ACTIVE COLLECTORS - THE ONLY PLACE TO REGISTER MODELS
# ============================================================================

ACTIVE_COLLECTORS = [
    # GPTCollector(),
    GroqCollector(),
    GeminiCollector(),
]

"""
CRITICAL NOTE:
- This list is the ONLY source of truth for registered models
- Collectors are instantiated ONCE at module load time
- The orchestrator queries this list, no hardcoding of model names
- Adding a new model requires only adding one line above

Do NOT:
✗ Import collectors directly outside this module
✗ Reference specific model names in orchestrator
✗ Hardcode model lists elsewhere in the codebase

DO:
✓ Add new collector instances to ACTIVE_COLLECTORS
✓ Use ACTIVE_COLLECTORS in orchestrator
✓ Reference models only via the registry
"""
