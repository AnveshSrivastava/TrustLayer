"""NLI-based contradiction detector for the hallucination detector.

Uses a cross-encoder NLI model to detect logical contradictions between
model responses. Also validates responses against provided context.
"""

import datetime
from typing import Optional, Dict, Any
from itertools import combinations

from sentence_transformers import CrossEncoder

from analyzers.base import BaseAnalyzer
from analyzers.utils import normalize_text

# Model configuration
NLI_MODEL = "cross-encoder/nli-deberta-v3-small"
CONTRADICTION_THRESHOLD = 0.6


class NLIAnalyzer(BaseAnalyzer):
    """Natural Language Inference (NLI) contradiction detector.

    Uses a cross-encoder to identify contradictions between model responses.
    Also validates responses against provided context if available.

    Analyzer Name: "nli_contradiction"

    Features:
        - Detects logical contradictions between responses
        - Computes entailment and neutral scores
        - Context validation when context is provided
        - Configurable contradiction threshold
        - Exception safety: never raises
    """

    analyzer_name = "nli_contradiction"

    def __init__(self):
        """Initialize the NLI analyzer with cross-encoder model."""
        try:
            self.model = CrossEncoder(NLI_MODEL, max_length=512)
        except Exception as exc:
            self.model = None
            self.init_error = str(exc)

    def analyze(
        self,
        responses: Dict[str, Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze contradictions between responses using NLI.

        Args:
            responses: Dict mapping model names to response dicts
            context: Optional context string for context validation

        Returns:
            Dict[str, Any]: Analysis result with NLI scores and contradiction detection

        Returns:
            {
                "analyzer_name": "nli_contradiction",
                "success": bool,
                "error": Optional[str],
                "pairwise_nli": {
                    "modelA_vs_modelB": {
                        "A_implies_B": {
                            "contradiction": float,
                            "entailment": float,
                            "neutral": float,
                            "label": str
                        },
                        "B_implies_A": {...},
                        "is_contradictory": bool
                    },
                    ...
                },
                "context_validation": {
                    "modelA": {
                        "label": str,
                        "confidence": float
                    },
                    ...
                },
                "any_contradiction_detected": bool,
                "max_contradiction_score": float,
                "models_analyzed": list[str],
                "timestamp": str (ISO UTC)
            }
        """
        try:
            # Check initialization
            if self.model is None:
                return {
                    "analyzer_name": self.analyzer_name,
                    "success": False,
                    "error": f"Model initialization failed: {getattr(self, 'init_error', 'Unknown error')}",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }

            # Extract successful responses only
            successful_responses = {
                model_name: resp
                for model_name, resp in responses.items()
                if resp.get("success", False)
            }

            # Check minimum threshold
            if len(successful_responses) < 2:
                return {
                    "analyzer_name": self.analyzer_name,
                    "success": False,
                    "error": "insufficient_models",
                    "models_analyzed": list(successful_responses.keys()),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }

            # Normalize response texts
            model_names = list(successful_responses.keys())
            texts = {
                name: normalize_text(successful_responses[name].get("response", ""))
                for name in model_names
            }

            # Skip if any text is empty
            if any(not text for text in texts.values()):
                return {
                    "analyzer_name": self.analyzer_name,
                    "success": False,
                    "error": "empty_response_text",
                    "models_analyzed": model_names,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }

            # =========================================================================
            # PAIRWISE NLI ANALYSIS
            # =========================================================================
            pairwise_nli: Dict[str, Any] = {}
            max_contradiction = 0.0
            any_contradiction = False

            for (model_a, model_b) in combinations(model_names, 2):
                text_a = texts[model_a]
                text_b = texts[model_b]

                # Run NLI: A implies B
                scores_a_to_b = self.model.predict([[text_a, text_b]])[0]
                nli_labels = ["contradiction", "entailment", "neutral"]
                result_a_to_b = {
                    label: round(float(score), 4)
                    for label, score in zip(nli_labels, scores_a_to_b)
                }

                # Run NLI: B implies A
                scores_b_to_a = self.model.predict([[text_b, text_a]])[0]
                result_b_to_a = {
                    label: round(float(score), 4)
                    for label, score in zip(nli_labels, scores_b_to_a)
                }

                # Determine labels
                label_a_to_b = nli_labels[scores_a_to_b.argmax()]
                label_b_to_a = nli_labels[scores_b_to_a.argmax()]

                # Compute contradiction score (max in both directions)
                contradiction_score = max(
                    result_a_to_b["contradiction"],
                    result_b_to_a["contradiction"]
                )

                # Track max contradiction
                max_contradiction = max(max_contradiction, contradiction_score)

                # Check if contradictory
                is_contradictory = contradiction_score > CONTRADICTION_THRESHOLD
                if is_contradictory:
                    any_contradiction = True

                # Store pairwise result
                key = f"{model_a}_vs_{model_b}"
                pairwise_nli[key] = {
                    f"{model_a}_implies_{model_b}": {
                        **result_a_to_b,
                        "label": label_a_to_b
                    },
                    f"{model_b}_implies_{model_a}": {
                        **result_b_to_a,
                        "label": label_b_to_a
                    },
                    "is_contradictory": is_contradictory,
                    "max_contradiction_score": contradiction_score
                }

            # =========================================================================
            # CONTEXT VALIDATION (if provided)
            # =========================================================================
            context_validation: Dict[str, Dict[str, Any]] = {}

            if context and context.strip():
                normalized_context = normalize_text(context)

                for model_name in model_names:
                    response_text = texts[model_name]

                    # Run NLI: context implies response
                    scores = self.model.predict([[normalized_context, response_text]])[0]
                    nli_labels = ["contradiction", "entailment", "neutral"]

                    result = {
                        label: round(float(score), 4)
                        for label, score in zip(nli_labels, scores)
                    }
                    label = nli_labels[scores.argmax()]
                    confidence = round(float(scores.max()), 4)

                    context_validation[model_name] = {
                        "label": label,
                        "confidence": confidence,
                        "scores": result
                    }

            # =========================================================================
            # BUILD RESPONSE
            # =========================================================================
            return {
                "analyzer_name": self.analyzer_name,
                "success": True,
                "error": None,
                "pairwise_nli": pairwise_nli,
                "context_validation": context_validation if context_validation else None,
                "any_contradiction_detected": any_contradiction,
                "max_contradiction_score": max_contradiction,
                "contradiction_threshold": CONTRADICTION_THRESHOLD,
                "models_analyzed": model_names,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        except Exception as exc:
            return {
                "analyzer_name": self.analyzer_name,
                "success": False,
                "error": f"Analysis failed: {str(exc)}",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
