"""Visual Architecture Diagrams for Hallucination Detector

This file contains ASCII diagrams showing the system architecture.
"""

# ============================================================================
# 1. SYSTEM ARCHITECTURE OVERVIEW
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HALLUCINATION DETECTOR                              │
│                      Production-Grade Architecture                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT REQUEST                                   │
│                      POST /analyze {query, context}                         │
└────────────────────────────────┬──────────────────────────────────────────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │   main.py      │
                        │  FastAPI App   │
                        └────────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │ Import collectors      │
                    │ (triggers registration)│
                    └────────────┬────────────┘
                                 │
                                 ▼
          ┌──────────────────────────────────────────────┐
          │      orchestrate_collection()                │
          │      (collectors/orchestrator.py)            │
          └────────────────┬─────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │  get_registry().get_all()   │
            │  (Core registry access)     │
            └──────────────┬──────────────┘
                           │
          ┌────────────────▼─────────────────┐
          │   DYNAMIC COLLECTOR DISCOVERY    │
          │   Fetch all registered collectors│
          │   No hardcoded model names!      │
          └────────────────┬─────────────────┘
                           │
          ┌────────────────▼─────────────────┐
          │   PARALLEL EXECUTION             │
          │   asyncio.gather() all tasks     │
          └─┬──────────────────┬──────────────┬┘
            │                  │              │
    ┌───────▼────┐    ┌────────▼─┐   ┌──────▼──────┐
    │    GPT     │    │  Claude  │   │   Gemini   │
    │ Collector  │    │Collector │   │ Collector  │
    └───────┬────┘    └────────┬─┘   └──────┬──────┘
            │                  │              │
            └────────────┬─────┴──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │   RESPONSE AGGREGATION      │
          │   Normalize responses       │
          │   Handle exceptions         │
          │   Build metadata            │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────────────┐
          │   STRUCTURED RESPONSE               │
          │   {                                 │
          │     "responses": {...},             │
          │     "metadata": {...},              │
          │     "status": "success"             │
          │   }                                 │
          └──────────────┬──────────────────────┘
                         │
                         ▼
                    ┌────────────┐
                    │   CLIENT   │
                    │  Response  │
                    └────────────┘
"""

# ============================================================================
# 2. DEPENDENCY GRAPH (LOOSE COUPLING)
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DEPENDENCY GRAPH                                   │
│                    (Showing Loose Coupling)                                 │
└─────────────────────────────────────────────────────────────────────────────┘

CLIENT
  │
  └──► main.py (FastAPI)
         │
         ├──► collectors/__init__.py
         │      ├──► gpt.py ──────┐
         │      ├──► claude.py ───┤
         │      └──► gemini.py ───┤
         │                        │
         │                        ▼
         │                   BaseCollector
         │                   (from core/)
         │
         ├──► orchestrator.py
         │      │
         │      └──► get_registry()
         │           (from core/)
         │
         └──► models.py
              (Pydantic schemas)

KEY PRINCIPLES:
✅ main.py doesn't import specific collectors (only __init__.py)
✅ Collectors import BaseCollector (shared interface)
✅ Orchestrator only imports get_registry()
✅ No circular imports
✅ No hardcoded model names in core logic
✅ All collectors are interchangeable
✅ Adding new model: only affects new file, no changes to core
"""

# ============================================================================
# 3. REGISTRY-BASED DISCOVERY
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│              REGISTRY-BASED COLLECTOR DISCOVERY                             │
│                    (Auto-Registration Pattern)                              │
└─────────────────────────────────────────────────────────────────────────────┘

IMPORT TIME:
════════════

from collectors import gpt, claude, gemini
             │          │       │         │
             │          │       │         └─► gemini.py
             │          │       │              │
             │          │       │              ├─► class GeminiCollector(BaseCollector)
             │          │       │              ├─► get_registry().register(collector)
             │          │       │              └─► ✅ Registered
             │          │       │
             │          │       └─► claude.py
             │          │            │
             │          │            ├─► class ClaudeCollector(BaseCollector)
             │          │            ├─► get_registry().register(collector)
             │          │            └─► ✅ Registered
             │          │
             │          └─► gpt.py
             │               │
             │               ├─► class GPTCollector(BaseCollector)
             │               ├─► get_registry().register(collector)
             │               └─► ✅ Registered
             │
             └─► __init__.py imports all above


RUNTIME:
════════

orchestrate_collection()
    │
    ├─► get_registry().get_all()
    │   │
    │   └─► Returns {
    │        "gpt": GPTCollector(),
    │        "claude": ClaudeCollector(),
    │        "gemini": GeminiCollector()
    │       }
    │
    ├─► For each collector, create async task
    │   │
    │   └─► collector.get_response(query, context)
    │
    ├─► await asyncio.gather(*tasks)
    │   │
    │   └─► Execute all in parallel
    │
    └─► Aggregate responses + metadata

BENEFITS:
✅ No hardcoded model names
✅ Collectors auto-discovered
✅ Fully dynamic at runtime
✅ Adding new model is automatic
✅ Removing model is automatic
"""

# ============================================================================
# 4. COLLECTOR LIFECYCLE
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                      COLLECTOR LIFECYCLE                                    │
│                    (From Creation to Response)                              │
└─────────────────────────────────────────────────────────────────────────────┘

1. CREATION (Module Load)
   ════════════════════════
   collectors/gpt.py loaded
        │
        ├─► class GPTCollector(BaseCollector):
        │       @property
        │       def model_name(self) -> str:
        │           return "gpt"
        │
        │       async def get_response(...) -> Dict:
        │           # Implementation
        │
        ├─► _gpt_collector = GPTCollector()
        │
        └─► get_registry().register(_gpt_collector)
                │
                └─► Registry adds to collectors dict:
                    {"gpt": _gpt_collector}


2. DISCOVERY (Runtime)
   ═══════════════════
   orchestrate_collection() called
        │
        ├─► registry = get_registry()
        │
        └─► collectors = registry.get_all()
                └─► Returns {"gpt": GPTCollector(), "claude": ..., ...}


3. EXECUTION (Parallel)
   ════════════════════
   For each collector in collectors.values():
        │
        ├─► task = collector.get_response(query, context)
        │
        └─► await asyncio.gather(*all_tasks)
                │
                ├─► GPTCollector.get_response()
                │   ├─► Call OpenAI API
                │   ├─► Handle timeout (10s)
                │   ├─► Handle retry (1x)
                │   └─► Return standardized response
                │
                ├─► ClaudeCollector.get_response()
                │   ├─► Call Anthropic API
                │   ├─► Handle timeout (10s)
                │   ├─► Handle retry (1x)
                │   └─► Return standardized response
                │
                └─► GeminiCollector.get_response()
                    ├─► Call Gemini API
                    ├─► Handle timeout (10s)
                    ├─► Handle retry (1x)
                    └─► Return standardized response


4. RESPONSE (Aggregation)
   ═════════════════════
   All responses collected
        │
        ├─► Normalize each response
        │   ├─► Check schema compliance
        │   ├─► Handle exceptions
        │   └─► Standardize format
        │
        ├─► Build metadata
        │   ├─► Total models
        │   ├─► Successful models
        │   ├─► Failed models
        │   ├─► Average latency
        │   └─► Timestamp
        │
        └─► Determine status
            ├─► "success" if all succeeded
            ├─► "partial failure" if some failed
            ├─► "failure" if all failed
            └─► "no collectors" if empty
"""

# ============================================================================
# 5. MODULE STRUCTURE
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MODULE STRUCTURE                                      │
│                    (Files and Relationships)                                │
└─────────────────────────────────────────────────────────────────────────────┘

CORE (Interfaces & Registry)
══════════════════════════════

  core/__init__.py
       │
       ├─► BaseCollector (from base_collector.py)
       │   └─► Abstract base class for all collectors
       │
       └─► get_registry() (from registry.py)
           └─► Access global singleton registry


COLLECTORS (Model Adapters)
═════════════════════════════

  collectors/__init__.py
       │
       ├─► Imports: gpt, claude, gemini
       │   (Triggers auto-registration)
       │
       ├─► gpt.py
       │   ├─► GPTCollector extends BaseCollector
       │   ├─► Calls OpenAI API
       │   └─► Auto-registers
       │
       ├─► claude.py
       │   ├─► ClaudeCollector extends BaseCollector
       │   ├─► Calls Anthropic API
       │   └─► Auto-registers
       │
       ├─► gemini.py
       │   ├─► GeminiCollector extends BaseCollector
       │   ├─► Calls Google API
       │   └─► Auto-registers
       │
       ├─► local_model.py
       │   ├─► LocalModelCollector extends BaseCollector
       │   ├─► Example implementation
       │   └─► Optional auto-registration
       │
       └─► orchestrator.py
           ├─► orchestrate_collection()
           ├─► Fetches from registry
           ├─► Executes parallel
           └─► Aggregates responses


ANALYZERS (Future Extension)
══════════════════════════════

  analyzers/__init__.py
       │
       ├─► semantic_analyzer.py (optional)
       ├─► consensus_engine.py (optional)
       └─► Other analyzers...


ENGINES (Future Extension)
═════════════════════════════

  engines/__init__.py
       │
       ├─► trust_engine.py (optional)
       ├─► scoring_engine.py (optional)
       └─► Other engines...


MAIN APPLICATION
═════════════════

  main.py
       │
       ├─► Import collectors (triggers registration)
       ├─► Call orchestrate_collection()
       └─► Return AnalysisResponse

  models.py
       │
       ├─► QueryInput (request schema)
       ├─► ModelResponse (single model response)
       ├─► CollectionMetadata (aggregated metadata)
       └─► AnalysisResponse (final response)

  config.py
       │
       └─► Load API keys from environment
"""

# ============================================================================
# 6. EXTENSIBILITY FLOW
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADDING A NEW COLLECTOR                                   │
│              (Extensibility - One File, Zero Changes)                       │
└─────────────────────────────────────────────────────────────────────────────┘

SCENARIO: Add a new model "MyModel"

STEP 1: Create ONE file
════════════════════════

  collectors/my_model.py
    ├─► from core import BaseCollector, get_registry
    ├─► class MyModelCollector(BaseCollector):
    ├─► @property model_name(self) -> str: return "my_model"
    ├─► async def get_response(self, query, context) -> Dict:
    │   └─► Your implementation here
    ├─► _collector = MyModelCollector()
    └─► get_registry().register(_collector)


STEP 2: Import in main.py
═══════════════════════════

  BEFORE:
    from collectors import gpt, claude, gemini

  AFTER:
    from collectors import gpt, claude, gemini, my_model
                                                   ^^^^^^^^

  That's it!


STEP 3: System works automatically
═══════════════════════════════════

  ✅ Registry discovers "my_model" collector
  ✅ Orchestrator includes it in parallel execution
  ✅ Responses include my_model output
  ✅ Metadata includes my_model performance

  NO CHANGES NEEDED:
    ✅ orchestrator.py - No changes
    ✅ analyzers/ - No changes
    ✅ engines/ - No changes
    ✅ config.py - No changes
    ✅ main.py logic - No changes
    ✅ models.py - No changes


RESULT:
═══════

  Response now includes:
  {
    "responses": {
      "gpt": {...},
      "claude": {...},
      "gemini": {...},
      "my_model": {...}  ◄── NEW!
    },
    "collection_metadata": {
      "total_models": 4,  ◄── Now 4
      ...
    }
  }
"""

# ============================================================================
# 7. DATA FLOW
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST/RESPONSE FLOW                               │
│                    (Complete End-to-End Data Journey)                       │
└─────────────────────────────────────────────────────────────────────────────┘

1. CLIENT REQUEST
   ════════════════
   POST /analyze
   {
     "query": "What is AI?",
     "context": "In healthcare",
     "expected_answer": null,
     "query_type": "factual",
     "metadata": {}
   }


2. FASTAPI HANDLER
   ═════════════════
   main.py::analyze()
     └─► Receive QueryInput
         └─► Call orchestrate_collection(query, context)


3. ORCHESTRATION
   ══════════════
   orchestrate_collection()
     │
     ├─► Get registry
     ├─► Get all collectors
     │   ├─► GPTCollector
     │   ├─► ClaudeCollector
     │   └─► GeminiCollector
     │
     ├─► Create async tasks
     │   └─► [gpt.get_response(...), claude.get_response(...), gemini.get_response(...)]
     │
     └─► Execute: await asyncio.gather(...)


4. PARALLEL EXECUTION
   ═══════════════════
   Task 1 (GPT)                    Task 2 (Claude)                 Task 3 (Gemini)
   ├─► Build prompt               ├─► Build prompt                ├─► Build prompt
   ├─► Call OpenAI API            ├─► Call Anthropic API          ├─► Call Google API
   ├─► Extract text               ├─► Extract text                ├─► Extract text
   ├─► Handle timeout             ├─► Handle timeout              ├─► Handle timeout
   ├─► Handle retry               ├─► Handle retry                ├─► Handle retry
   └─► Return response            └─► Return response             └─► Return response


5. RESPONSE COLLECTION
   ════════════════════
   Results from all tasks:
   [
     {"model": "gpt", "response": "...", "success": true, "latency_ms": 1250},
     {"model": "claude", "response": "...", "success": true, "latency_ms": 1300},
     {"model": "gemini", "response": "...", "success": true, "latency_ms": 1400}
   ]


6. RESPONSE AGGREGATION
   ═════════════════════
   Normalize each response:
     ├─► Check schema compliance
     ├─► Handle exceptions
     └─► Validate required fields

   Build metadata:
     ├─► total_models: 3
     ├─► successful_models: 3
     ├─► failed_models: []
     ├─► average_latency_ms: 1316.7
     ├─► max_latency_ms: 1400
     └─► timestamp: "2024-04-21T10:30:00Z"

   Determine status:
     └─► "success" (all models succeeded)


7. FINAL RESPONSE
   ══════════════
   {
     "query": "What is AI?",
     "responses": {
       "gpt": {
         "model": "gpt",
         "response": "AI is artificial intelligence...",
         "success": true,
         "error": null,
         "latency_ms": 1250
       },
       "claude": {
         "model": "claude",
         "response": "Artificial intelligence refers to...",
         "success": true,
         "error": null,
         "latency_ms": 1300
       },
       "gemini": {
         "model": "gemini",
         "response": "AI is a broad field that encompasses...",
         "success": true,
         "error": null,
         "latency_ms": 1400
       }
     },
     "status": "success",
     "collection_metadata": {
       "total_models": 3,
       "successful_models": 3,
       "failed_models": [],
       "average_latency_ms": 1316.7,
       "max_latency_ms": 1400,
       "timestamp": "2024-04-21T10:30:00Z"
     }
   }


8. CLIENT RECEIVES RESPONSE
   ════════════════════════
   Full structured data with:
     ✅ Responses from all models
     ✅ Success indicators
     ✅ Error messages (if any)
     ✅ Latency information
     ✅ Metadata about collection
     ✅ Overall status
"""

# ============================================================================
# 8. EXCEPTION HANDLING FLOW
# ============================================================================

"""
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXCEPTION HANDLING                                    │
│               (One Model Failure Doesn't Crash System)                       │
└─────────────────────────────────────────────────────────────────────────────┘

SCENARIO: Gemini API timeout, GPT and Claude succeed

WITHOUT REGISTRY-BASED ARCHITECTURE (BAD):
═════════════════════════════════════════

  collect_responses():
    gpt_resp = await gpt.get_response(...)  ✅ Success
    
    claude_resp = await claude.get_response(...)  ✅ Success
    
    gemini_resp = await gemini.get_response(...)  ❌ TIMEOUT
                                                   │
                                                   ├─► Exception raised
                                                   ├─► No try/catch
                                                   └─► Function crashes
    
    ❌ No response collected
    ❌ Client gets error
    ❌ GPT and Claude responses are lost


WITH REGISTRY-BASED ARCHITECTURE (GOOD):
═════════════════════════════════════════

  orchestrate_collection():
    collectors = registry.get_all()
    
    tasks = [
      gpt.get_response(...),      ✅ Task 1
      claude.get_response(...),   ✅ Task 2
      gemini.get_response(...)    ❌ Task 3 (will timeout)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
                    │                       │
                    └───────┬───────────────┘
                            │
                            ├─► gpt result: {"success": true, "response": "..."}
                            ├─► claude result: {"success": true, "response": "..."}
                            └─► gemini exception: TimeoutError("Timeout after 10s")
    
    Normalize each result:
      ├─► gpt → {"model": "gpt", "response": "...", "success": true, "error": null}
      ├─► claude → {"model": "claude", "response": "...", "success": true, "error": null}
      └─► gemini (exception) → {"model": "gemini", "response": "", "success": false, "error": "Timeout after 10s"}
    
    Build metadata:
      {
        "total_models": 3,
        "successful_models": 2,
        "failed_models": ["gemini"],
        "average_latency_ms": 1275,
        "timestamp": "2024-04-21T10:30:00Z"
      }
    
    Determine status: "partial failure"
    
    ✅ Client receives response with:
       - GPT response included
       - Claude response included
       - Gemini failure documented
       - Metadata shows what happened
"""

# ============================================================================

print(__doc__)
