# Hallucination Detector: Production Architecture

## Overview

The hallucination-detector is a **production-grade, modular, and loosely coupled** AI system built on strict architectural principles:

- **Loose Coupling**: Modules interact only through well-defined interfaces
- **High Cohesion**: Each module has a single, focused responsibility
- **Interface-Driven Design**: All components conform to abstract base classes
- **N-Model Scalability**: Support unlimited models without core changes
- **Dynamic Extensibility**: Add/remove models without touching existing logic

## Core Design Principles

### 1. No Hardcoded Dependencies

The system has **zero hardcoded model names** in the core logic. All collectors are registered dynamically at runtime through a central registry.

```python
# ❌ BAD: Hardcoded model names (old approach)
async def collect_responses(query):
    gpt_resp = await gpt.get_response(query)
    claude_resp = await claude.get_response(query)
    gemini_resp = await gemini.get_response(query)
    return {gpt_resp, claude_resp, gemini_resp}

# ✅ GOOD: Dynamic registry-based approach (new approach)
async def orchestrate_collection(query):
    collectors = get_registry().get_all()
    results = await asyncio.gather(*[
        c.get_response(query) for c in collectors.values()
    ])
    return results
```

### 2. Interface-Driven Contracts

All collectors inherit from a strict abstract base class that enforces a contract:

```python
class BaseCollector(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        pass
```

**Response Schema** (Enforced):
```python
{
    "model": str,              # Model identifier
    "response": str,           # Text response
    "success": bool,           # Success indicator
    "error": Optional[str],    # Error message
    "latency_ms": int          # Latency in milliseconds
}
```

### 3. Dynamic Registry Pattern

The registry maintains a thread-safe mapping of collectors and provides a singleton interface:

```python
registry = get_registry()

# At import time (auto-registration)
registry.register(GPTCollector())

# At runtime (dynamic discovery)
collectors = registry.get_all()  # Get all collectors
collector = registry.get("gpt")  # Get specific collector
```

## Project Structure

```
hallucination-detector/
├── core/                    # Shared interfaces + registry
│   ├── __init__.py
│   ├── base_collector.py   # Abstract base class for collectors
│   └── registry.py         # Dynamic collector registry
│
├── collectors/              # Model adapters (plug-and-play)
│   ├── __init__.py         # Package initialization
│   ├── gpt.py              # OpenAI GPT collector
│   ├── claude.py           # Anthropic Claude collector
│   ├── gemini.py           # Google Gemini collector
│   ├── local_model.py      # Example: Local model (extensibility demo)
│   ├── collector.py        # (Legacy) Backward-compatible module
│   └── orchestrator.py     # Registry-based orchestrator
│
├── analyzers/               # Semantic analysis modules
│   └── __init__.py
│
├── engines/                 # Trust scoring & consensus engines
│   └── __init__.py
│
├── classifier/              # Hallucination classification
│   └── __init__.py
│
├── data/                    # Data handling modules
│   └── __init__.py
│
├── notebooks/               # Jupyter notebooks
│   └── __init__.py
│
├── main.py                  # FastAPI entry point
├── models.py                # Pydantic models for API schemas
├── config.py                # Configuration management
└── requirements.txt         # Dependencies
```

## Adding a New Collector

To add a new LLM model to the system, you need to create **ONE new file**. Zero changes to existing logic.

### Step 1: Create a New Collector File

Create `collectors/my_model.py`:

```python
"""My Model collector for the hallucination detector."""

import asyncio
import time
from typing import Optional, Dict, Any

from core import BaseCollector, get_registry


class MyModelCollector(BaseCollector):
    """My Model implementation."""

    @property
    def model_name(self) -> str:
        return "my_model"

    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get response from My Model."""
        started_at = time.monotonic()
        
        try:
            # Your model inference logic here
            response_text = await self._call_model(query, context)
            success = True
            error = None
        except Exception as exc:
            response_text = ""
            success = False
            error = str(exc)

        latency_ms = int((time.monotonic() - started_at) * 1000)
        return {
            "model": self.model_name,
            "response": response_text if success else "",
            "success": success,
            "error": error,
            "latency_ms": latency_ms,
        }

    async def _call_model(self, query: str, context: Optional[str]) -> str:
        """Call your model implementation here."""
        # TODO: Implement your model inference
        pass


# Auto-register
_collector = MyModelCollector()
get_registry().register(_collector)
```

### Step 2: Import in Main

That's it! Just import your module in `collectors/__init__.py` or `main.py`:

```python
from collectors import my_model
```

### Step 3: Done!

The system automatically:
- ✅ Discovers your collector via auto-registration
- ✅ Includes it in orchestration
- ✅ Returns responses with metadata
- ✅ Handles timeouts and errors

**No changes needed** to:
- Orchestrator
- Analyzers
- Engines
- FastAPI routes
- Configuration

## Architecture Benefits

### 1. **Loose Coupling**
- Collectors are isolated modules
- Orchestrator doesn't know specific models
- Easy to test each component independently

### 2. **High Cohesion**
- Each collector handles one model
- Each module has a single responsibility
- Clear separation of concerns

### 3. **Extensibility**
- Add new models by creating one file
- Remove models by unregistering
- No cascading changes

### 4. **Scalability**
- Support unlimited models
- Registry is thread-safe
- Parallel execution via asyncio

### 5. **Maintainability**
- Clear contracts via BaseCollector
- Standardized response schema
- Exception safety built-in
- Type hints everywhere

## Key Files

### `core/base_collector.py`
Abstract base class defining the collector interface. All collectors must inherit from this class.

**Why it matters**: Enforces a strict contract that all collectors follow.

### `core/registry.py`
Thread-safe registry for dynamic collector management. Provides:
- `register(collector)`: Register a new collector
- `get_all()`: Get all registered collectors
- `get(model_name)`: Get a specific collector
- `unregister(model_name)`: Remove a collector
- `is_registered(model_name)`: Check if registered
- `list_models()`: List all model names

**Why it matters**: Enables runtime discovery without hardcoded imports.

### `collectors/orchestrator.py`
Registry-based orchestrator that:
1. Fetches collectors from registry
2. Executes all in parallel via `asyncio.gather()`
3. Normalizes exceptions and responses
4. Builds metadata (latency, success rate, etc.)
5. Returns structured response

**Why it matters**: Orchestration logic is completely decoupled from specific models.

### Specific Collectors (`collectors/gpt.py`, `claude.py`, `gemini.py`)
Each collector:
- Inherits from `BaseCollector`
- Implements `get_response()` async method
- Handles timeouts (10s) and retries (1 retry)
- Returns standardized schema
- Auto-registers at import time

**Why it matters**: Models are interchangeable plugins.

### `main.py`
FastAPI entry point that:
1. Imports collectors to trigger registration
2. Calls `orchestrate_collection()` from orchestrator
3. Returns structured `AnalysisResponse`

**Why it matters**: Business logic is minimal and doesn't reference specific models.

## Example: End-to-End Flow

```
1. User sends HTTP POST /analyze
   {
       "query": "What is AI?",
       "context": "In the context of healthcare..."
   }

2. FastAPI handler receives QueryInput
   - Imports collectors (auto-registers all)
   - Calls orchestrate_collection(query, context)

3. Orchestrator:
   - Calls get_registry().get_all()
   - Returns {gpt: GPTCollector(), claude: ClaudeCollector(), ...}
   - Creates async tasks for each: [gpt.get_response(...), claude.get_response(...), ...]
   - Executes all in parallel: await asyncio.gather(*tasks)
   - Normalizes exceptions
   - Builds metadata

4. Response returned:
   {
       "query": "What is AI?",
       "responses": {
           "gpt": {"model": "gpt", "response": "...", "success": true, ...},
           "claude": {...},
           "gemini": {...}
       },
       "status": "success",
       "collection_metadata": {
           "total_models": 3,
           "successful_models": 3,
           "average_latency_ms": 1250.5,
           ...
       }
   }
```

## Testing Extensibility

### Test 1: Add a Local Model
1. Create `collectors/local_model.py` with `LocalModelCollector`
2. Auto-register at bottom of file
3. Import in `main.py`
4. ✅ System works automatically - no changes to orchestrator, analyzers, or engines

### Test 2: Disable a Model
1. Comment out import in `collectors/__init__.py`
2. ✅ System works with remaining models - no changes needed

### Test 3: Add Multiple Models
1. Create `collectors/model_a.py`, `collectors/model_b.py`, etc.
2. Auto-register each
3. ✅ System scales automatically

## Strict Constraints Enforced

✅ **No circular imports**: Registry is separate, core module provides single entry point

✅ **No hardcoded model names**: Orchestrator is model-agnostic

✅ **No logic duplication**: Each collector has single responsibility

✅ **Independent testability**: Each module can be tested in isolation

✅ **Type hints everywhere**: Full type annotation for IDE support

✅ **Exception safety**: No collector can crash the system

✅ **Async-compatible**: All operations use async/await

## Configuration

All API keys are loaded from `.env`:

```bash
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI-...
```

Configuration is centralized in `config.py` and validated at import time.

## Response Schema

All API endpoints return `AnalysisResponse`:

```python
class AnalysisResponse(BaseModel):
    query: str
    responses: Dict[str, ModelResponse]  # {model_name: response}
    status: str                           # "success", "partial failure", etc.
    collection_metadata: CollectionMetadata
```

Each `ModelResponse`:
```python
{
    "model": str,           # Model identifier
    "response": str,        # Text response
    "success": bool,        # Success indicator
    "error": Optional[str], # Error if failed
    "latency_ms": int       # Latency
}
```

## Future Extensions

This architecture easily supports:

1. **Model Weighting**: Assign confidence scores per model
2. **Consensus Engines**: Aggregate responses based on agreement
3. **Trust Scoring**: Compute trust scores from multiple models
4. **Semantic Analysis**: Analyze semantic similarity
5. **Hallucination Detection**: Identify factual inconsistencies
6. **A/B Testing**: Compare model performance
7. **Custom Analyzers**: Add domain-specific analysis

All without modifying core logic.

## Performance Characteristics

- **Parallel Execution**: All models queried simultaneously
- **Timeout Protection**: 10-second timeout per model
- **Automatic Retry**: 1 automatic retry on failure
- **Exception Safety**: Failures isolated to specific collectors
- **Latency Tracking**: Full request latency per model
- **Metadata Aggregation**: Real-time statistics

## Conclusion

This architecture demonstrates **production-grade design** that balances:

- **Simplicity**: Easy to understand and extend
- **Flexibility**: Dynamic model management
- **Robustness**: Exception handling and timeouts
- **Scalability**: Support unlimited models
- **Maintainability**: Clear separation of concerns

Adding a new model takes **one file and zero changes to core logic**.
