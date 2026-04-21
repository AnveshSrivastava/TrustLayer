"""
PRODUCTION-GRADE ANALYZER FRAMEWORK
===================================

This document explains the production enhancements to the analyzer framework.

================================================================================
1. STRICT MODE CONFIGURATION
================================================================================

Location: analyzers/registry.py

STRICT_MODE = False  (current setting)

Behavior:
- True:  Analyzer failures raise exceptions (fail fast, good for research)
- False: Analyzer failures print warnings (graceful degradation, production)

To switch modes:
    # In analyzers/registry.py
    STRICT_MODE = True   # for fail-fast mode
    STRICT_MODE = False  # for graceful degradation

When to use:
- STRICT_MODE = True:  During development and research (catch issues early)
- STRICT_MODE = False: In production (avoid cascade failures)

================================================================================
2. LAZY LOADING & SAFE INSTANTIATION
================================================================================

How it works:
- Analyzers are registered as CLASSES (not instances) in ACTIVE_ANALYZER_CLASSES
- Instances are created only when run_analyzers() is called
- Each request gets fresh analyzer instances
- Failures are isolated per analyzer (one failure doesn't crash others)

Benefits:
- No model loading at import time (fast app startup)
- No memory waste on unused models
- Clean separation of concerns
- Excellent for serverless deployments

Code:
    from analyzers.analyzer import run_analyzers
    
    result = run_analyzers(responses, context)
    # Analyzers instantiated here, not at import time

================================================================================
3. EXECUTION TIME TRACKING
================================================================================

All analyzers now report execution_time_ms:

Per-Analyzer Timing:
    result = {
        "analyzer_name": "semantic_similarity",
        "success": True,
        "execution_time_ms": 1234,  # <-- New field
        ...
    }

Aggregate Timing:
    metadata = {
        "total_analyzers": 2,
        "successful_analyzers": 2,
        "total_execution_time_ms": 5678,  # <-- Orchestration time
        "timestamp": "2026-04-21T...",
    }

Timing includes:
- Analyzer instantiation
- Model loading (if not cached)
- Analysis computation
- Exception handling (if failed)

Use cases:
- Monitor analyzer performance
- Identify bottlenecks
- SLA tracking
- Cost analysis (slower = more expensive)

================================================================================
4. WARMUP FUNCTION (Critical for Production)
================================================================================

Purpose: Eagerly load all analyzer models during application startup

Location: analyzers/registry.py

Function:
    def warmup_analyzers() -> None:
        """Instantiate all analyzers to force model loading."""

Called by:
    main.py @app.on_event("startup")

Behavior:
    STRICT_MODE = True:
        - Raises exception if any analyzer fails to load
        - Prevents app startup (fail fast)
    
    STRICT_MODE = False:
        - Prints warnings for failed analyzers
        - App continues to start

Benefits:
- Models load ONCE during startup
- No cold starts on first request
- Predictable response times
- Failures detected before handling requests

Logs:
    ✓ Warmup: SimilarityAnalyzer loaded successfully
    ✓ Warmup: NLIAnalyzer loaded successfully
    ✓ Startup complete: All analyzers ready

================================================================================
5. FASTAPI STARTUP HOOK
================================================================================

Location: main.py

Code:
    @app.on_event("startup")
    async def startup_event():
        from analyzers.registry import warmup_analyzers
        warmup_analyzers()

When it runs:
    1. Application starts
    2. Startup hook executes
    3. All analyzers warmed up
    4. Application ready for requests

Timing:
    - Happens ONCE when app starts
    - BEFORE first request arrives
    - Typical duration: 2-5 seconds (depends on model sizes)

================================================================================
6. METADATA ENHANCEMENT
================================================================================

Response structure now includes execution metrics:

    /analyze response:
    {
        "query": "What is AI?",
        "responses": {...models responses...},
        "status": "success",
        "collection_metadata": {
            "total_models": 3,
            "successful_models": 3,
            "average_latency_ms": 1500.0,
            ...
        },
        "analysis": {
            "semantic_similarity": {
                "success": True,
                "execution_time_ms": 1234,  # <-- Per-analyzer timing
                "average_similarity": 0.85,
                ...
            },
            "nli_contradiction": {
                "success": True,
                "execution_time_ms": 2345,  # <-- Per-analyzer timing
                "any_contradiction_detected": False,
                ...
            }
        },
        "analysis_metadata": {
            "total_analyzers": 2,
            "successful_analyzers": 2,
            "failed_analyzers": [],
            "total_execution_time_ms": 3579,  # <-- Total time
            "timestamp": "2026-04-21T..."
        }
    }

================================================================================
7. PRODUCTION DEPLOYMENT CHECKLIST
================================================================================

Before deploying to production:

[ ] 1. Review STRICT_MODE setting
    - Set to False for graceful degradation
    - Or True if you want fail-fast behavior

[ ] 2. Test startup with docker-compose or kubernetes
    - Ensure warmup completes successfully
    - Verify models load correctly
    - Check logs for any warnings

[ ] 3. Monitor analyzer execution times
    - Set up dashboards for execution_time_ms
    - Alert if execution_time_ms > threshold
    - Track performance trends

[ ] 4. Test with expected load
    - Verify no memory leaks
    - Check if models need to be reloaded
    - Monitor GPU usage (if applicable)

[ ] 5. Set up logging & alerting
    - Monitor "Startup: Warming up" log
    - Alert on startup failures
    - Track per-analyzer error rates

[ ] 6. Document API response format
    - Include execution_time_ms in docs
    - Explain analysis_metadata
    - Document expected timing

================================================================================
8. SCALING CONSIDERATIONS
================================================================================

Adding new analyzers:

1. Create: analyzers/my_analyzer.py
2. Register in analyzers/registry.py (_initialize_analyzers):
    
    try:
        from analyzers.my_analyzer import MyAnalyzer
        ACTIVE_ANALYZER_CLASSES.append(MyAnalyzer)
    except Exception as exc:
        if STRICT_MODE:
            raise
        else:
            print(f"Warning: {exc}")

3. That's it! No other changes needed.

Performance considerations:
- Analyzers run SEQUENTIALLY (not parallel)
- Total time ≈ sum of all analyzer times
- Adding analyzer N increases response time
- Consider async analyzers in future (requires new design)

Typical timing:
- Similarity analyzer: 500-2000ms (depends on embeddings)
- NLI analyzer: 1000-3000ms (depends on model size)
- Total with 2 analyzers: 2000-5000ms (sequential)

================================================================================
9. TROUBLESHOOTING
================================================================================

Issue: Startup fails with "Model loading failed"
Solution: Check logs, verify STRICT_MODE, ensure GPU memory available

Issue: Cold start on first request
Solution: Ensure warmup_analyzers() is called at startup

Issue: Execution time very high (>10s)
Solution: Check model sizes, verify GPU availability, consider caching

Issue: Memory usage increasing over time
Solution: Ensure models are not reloaded, check for memory leaks

Issue: "Could not load SimilarityAnalyzer"
Solution: This is expected if sentence-transformers has version conflicts
         System will gracefully degrade (if STRICT_MODE=False)

================================================================================
10. MONITORING & OBSERVABILITY
================================================================================

Key metrics to track:

1. Startup time
   - Time to warmup_analyzers() completion
   - Should be <10 seconds for typical models

2. Request latency
   - Collection time (from collection_metadata)
   - Analysis time (from analysis_metadata.total_execution_time_ms)
   - Total time (collection + analysis)

3. Per-analyzer metrics
   - execution_time_ms for each analyzer
   - success rate
   - error types and frequency

4. System metrics
   - Memory usage (MB)
   - CPU usage (%)
   - GPU usage (if applicable)

Example monitoring query (Prometheus):
    histogram_quantile(0.95, analysis_execution_time_ms)
    # P95 latency of analysis phase

================================================================================
"""
