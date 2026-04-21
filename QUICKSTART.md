# Quick Start Guide: Hallucination Detector

## 5-Minute Setup

### Prerequisites
- Python 3.9+
- pip or conda

### Step 1: Install Dependencies

```bash
cd hallucination-detector
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
```

Or use existing `.env`:
```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env  # or your preferred editor
```

### Step 3: Verify Registry

Run demonstration:

```bash
python DEMO.py
```

Expected output: Architecture explanation and verification that extensibility works.

### Step 4: Run Tests

```bash
pytest tests.py -v
```

Expected: All tests pass (mocks, no API calls needed).

### Step 5: Start Server

```bash
uvicorn main:app --reload
```

Expected: Server running at http://localhost:8000

### Step 6: Try API

```bash
# Health check
curl http://localhost:8000/health

# Analyze query
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is artificial intelligence?",
    "context": "In the context of machine learning"
  }'
```

---

## API Endpoints

### GET /health
Health check endpoint.

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

### GET /
API information.

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "name": "Hallucination Detector API",
  "version": "1.0.0"
}
```

### POST /analyze
Main endpoint: Collect responses from all models.

**Request:**
```json
{
  "query": "What is AI?",
  "context": "In healthcare",
  "expected_answer": null,
  "query_type": "factual",
  "metadata": {}
}
```

**Response:**
```json
{
  "query": "What is AI?",
  "responses": {
    "gpt": {
      "model": "gpt",
      "response": "AI is...",
      "success": true,
      "error": null,
      "latency_ms": 1250
    },
    "claude": {...},
    "gemini": {...}
  },
  "status": "success",
  "collection_metadata": {
    "total_models": 3,
    "successful_models": 3,
    "failed_models": [],
    "average_latency_ms": 1300.5,
    "max_latency_ms": 1500,
    "timestamp": "2024-04-21T10:30:00Z"
  }
}
```

---

## Understanding the Architecture

### Key Components

**1. Core Module** (`core/`)
- `BaseCollector` - Abstract interface for all collectors
- `get_registry()` - Access dynamic collector registry

**2. Collectors** (`collectors/`)
- `gpt.py` - OpenAI GPT collector
- `claude.py` - Anthropic Claude collector
- `gemini.py` - Google Gemini collector
- `orchestrator.py` - Orchestrates all collectors

**3. Business Logic** (`main.py`)
- FastAPI endpoints
- Calls orchestrator
- Returns responses

### Data Flow

```
Client Request
    ↓
POST /analyze
    ↓
main.py → orchestrate_collection()
    ↓
orchestrator.py:
  1. Get all collectors from registry
  2. Execute all in parallel
  3. Normalize responses
  4. Build metadata
    ↓
Response to Client
  {
    "query": "...",
    "responses": {model responses},
    "collection_metadata": {...}
  }
```

### Key Principle: No Hardcoding

Orchestrator doesn't know about specific models:

```python
# ❌ BAD (hardcoded)
result1 = await gpt.get_response(query)
result2 = await claude.get_response(query)
result3 = await gemini.get_response(query)

# ✅ GOOD (dynamic registry)
collectors = get_registry().get_all()
results = await asyncio.gather(*[
    c.get_response(query) for c in collectors.values()
])
```

---

## Adding a New Model

### Example: Add LLaMA Model

**Step 1:** Create `collectors/llama.py`

```python
"""LLaMA collector for hallucination detector."""

import asyncio
import time
from typing import Optional, Dict, Any

from core import BaseCollector, get_registry


class LLaMACollector(BaseCollector):
    """LLaMA model collector."""

    @property
    def model_name(self) -> str:
        return "llama"

    async def get_response(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get response from LLaMA model."""
        started_at = time.monotonic()
        
        try:
            # Your LLaMA inference code here
            response_text = await self._call_llama(query, context)
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

    async def _call_llama(self, query: str, context: Optional[str]) -> str:
        """Call your LLaMA implementation."""
        # TODO: Implement LLaMA inference
        return "LLaMA response"


# Auto-register
_llama_collector = LLaMACollector()
get_registry().register(_llama_collector)
```

**Step 2:** Import in `main.py`

```python
from collectors import gpt, claude, gemini, llama  # Add llama
```

**Step 3:** Done!

System automatically:
- ✅ Discovers LLaMA collector
- ✅ Includes in orchestration
- ✅ Returns responses with metadata

---

## Extending the System

### Adding Analyzers

Create `analyzers/semantic_analyzer.py`:

```python
from typing import Dict, List, Any


class SemanticAnalyzer:
    """Analyze semantic similarity between responses."""

    def analyze(self, responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze responses for semantic similarity."""
        # Extract text from responses
        texts = [
            r["response"] for r in responses.values() if r["success"]
        ]
        
        # Your semantic analysis logic here
        similarity_matrix = self._compute_similarity(texts)
        
        return {
            "similarity_matrix": similarity_matrix,
            "consensus_score": self._compute_consensus(similarity_matrix)
        }
    
    def _compute_similarity(self, texts: List[str]) -> List[List[float]]:
        # TODO: Implement semantic similarity
        pass
    
    def _compute_consensus(self, matrix: List[List[float]]) -> float:
        # TODO: Implement consensus scoring
        pass
```

**Use in main.py:**
```python
from analyzers.semantic_analyzer import SemanticAnalyzer

analyzer = SemanticAnalyzer()

@app.post("/analyze")
async def analyze(query: QueryInput) -> AnalysisResponse:
    result = await orchestrate_collection(query.query, query.context)
    
    # Add semantic analysis
    semantic_analysis = analyzer.analyze(result["responses"])
    result["semantic_analysis"] = semantic_analysis
    
    return AnalysisResponse(**result)
```

### Adding Engines

Create `engines/trust_engine.py`:

```python
from typing import Dict, Any


class TrustEngine:
    """Compute trust scores for responses."""

    def compute_trust_scores(self, responses: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Compute trust score for each response."""
        scores = {}
        
        for model_name, response in responses.items():
            score = self._compute_score(response)
            scores[model_name] = score
        
        return scores
    
    def _compute_score(self, response: Dict[str, Any]) -> float:
        """Compute trust score for single response."""
        if not response["success"]:
            return 0.0
        
        # Your trust computation logic
        # Consider: latency, confidence, model track record, etc.
        base_score = 0.8
        latency_penalty = min(response["latency_ms"] / 10000, 0.2)
        
        return base_score - latency_penalty
```

---

## Testing

### Run All Tests

```bash
pytest tests.py -v
```

### Run Specific Test

```bash
pytest tests.py::TestCollectorRegistry::test_registry_singleton -v
```

### Run with Coverage

```bash
pytest tests.py --cov=core --cov=collectors.orchestrator --cov-report=html
```

### Write Custom Test

```python
import pytest
from core import BaseCollector, get_registry


@pytest.mark.asyncio
async def test_custom_collector():
    """Test your custom collector."""
    
    class TestCollector(BaseCollector):
        @property
        def model_name(self) -> str:
            return "test"
        
        async def get_response(self, query: str, context=None):
            return {
                "model": "test",
                "response": "Test response",
                "success": True,
                "error": None,
                "latency_ms": 100
            }
    
    registry = get_registry()
    registry.register(TestCollector())
    
    collector = registry.get("test")
    response = await collector.get_response("test query")
    
    assert response["success"] is True
    assert response["model"] == "test"
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'core'"

**Solution:** Ensure you're running from `hallucination-detector` directory.

```bash
cd hallucination-detector
python main.py  # or uvicorn main:app
```

### Issue: "No collector registered for model 'X'"

**Solution:** Ensure collector is imported before use.

In `main.py`:
```python
# Add this at top
from collectors import gpt, claude, gemini  # Triggers auto-registration
```

### Issue: API returns 422 Unprocessable Entity

**Solution:** Check request JSON format. Example:

```bash
# ✅ Correct
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?"}'

# ❌ Wrong - missing required field
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Issue: "ANTHROPIC_API_KEY not found"

**Solution:** Ensure `.env` file exists and has API keys:

```bash
# Check .env exists
ls -la .env

# Check content (don't commit!)
cat .env

# If missing, create:
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
echo "OPENAI_API_KEY=sk-..." >> .env
echo "GEMINI_API_KEY=AIza..." >> .env
```

### Issue: Tests fail with "No API key in environment"

**Solution:** Tests use mocks - they shouldn't need API keys. If failing:

```bash
# Ensure running from correct directory
cd hallucination-detector

# Ensure pytest is installed
pip install pytest pytest-asyncio

# Run again
pytest tests.py -v
```

---

## Documentation

- **ARCHITECTURE.md** - Complete system design
- **MIGRATION.md** - Upgrade guide from old system
- **IMPLEMENTATION_SUMMARY.md** - What was implemented
- **DEMO.py** - Architecture demonstration
- **tests.py** - Unit tests and examples

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `main.py` | FastAPI entry point |
| `models.py` | Pydantic schemas |
| `config.py` | Configuration management |
| `core/base_collector.py` | Abstract collector interface |
| `core/registry.py` | Dynamic collector registry |
| `collectors/orchestrator.py` | Orchestration logic |
| `collectors/gpt.py` | GPT collector |
| `collectors/claude.py` | Claude collector |
| `collectors/gemini.py` | Gemini collector |

---

## Common Tasks

### Change Model Timeout

In each collector file, update:

```python
TIMEOUT_SECONDS = 10.0  # Change to desired timeout
```

### Add Retry Logic

In each collector, modify:

```python
async def _invoke_with_retry(prompt: str) -> Any:
    for attempt in range(2):  # Change to desired retry count
        try:
            # ...
```

### Change API Configuration

Edit `config.py`:

```python
required_keys = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY']
# Add or remove keys as needed
```

### Enable/Disable a Model

**Disable:**
```python
# In main.py, comment out import
# from collectors import gpt

# Or in collectors/__init__.py
# from collectors import gpt
```

**Enable:**
```python
# Uncomment the import
from collectors import gpt
```

---

## Performance Tips

### 1. Parallel Execution (Already Optimized)
The system executes all collectors in parallel by default using `asyncio.gather()`.

### 2. Caching Responses
Add caching layer if needed:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
async def cached_analyze(query: str):
    return await orchestrate_collection(query)
```

### 3. Batch Processing
Process multiple queries:

```python
queries = ["Query 1", "Query 2", "Query 3"]
results = await asyncio.gather(*[
    orchestrate_collection(q) for q in queries
])
```

---

## Next Steps

1. **Understand Architecture** - Read ARCHITECTURE.md
2. **Run Demonstration** - Execute DEMO.py
3. **Test Integration** - Run pytest tests.py
4. **Start Server** - Run uvicorn
5. **Try API** - Make sample requests
6. **Add Analyzers** - Create semantic analysis
7. **Deploy** - Use Docker or cloud platform

---

## Support & Resources

- **Architecture Details** - See ARCHITECTURE.md
- **Adding Models** - See MIGRATION.md
- **Code Examples** - See collectors/local_model.py
- **Unit Tests** - See tests.py
- **API Schema** - View /docs after starting server

---

**Happy analyzing! 🚀**
