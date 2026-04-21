"""Semantic similarity analyzer for the hallucination detector.

Uses sentence-transformers to compute embeddings and pairwise cosine similarity
between model responses. This helps identify consensus across different LLMs.
"""

import datetime
from typing import Optional, Dict, Any
from itertools import combinations

from sentence_transformers import SentenceTransformer, util

from analyzers.base import BaseAnalyzer
from analyzers.utils import normalize_text

# Model configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class SimilarityAnalyzer(BaseAnalyzer):
    """Semantic similarity analyzer.

    Computes pairwise cosine similarity between model responses using
    sentence-transformers embeddings. This identifies how similar different
    models' responses are to each other.

    Analyzer Name: "semantic_similarity"

    Features:
        - Loads embeddings model once at initialization
        - Computes pairwise cosine similarity
        - Provides average, min, max similarity scores
        - Normalized text input
        - Exception safety: never raises
    """

    analyzer_name = "semantic_similarity"

    def __init__(self):
        """Initialize the similarity analyzer with pre-trained embedding model."""
        try:
            self.model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as exc:
            self.model = None
            self.init_error = str(exc)

    def analyze(
        self,
        responses: Dict[str, Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze semantic similarity between responses.

        Args:
            responses: Dict mapping model names to response dicts
            context: Optional context (unused in this analyzer)

        Returns:
            Dict[str, Any]: Analysis result with pairwise scores and statistics

        Returns:
            {
                "analyzer_name": "semantic_similarity",
                "success": bool,
                "error": Optional[str],
                "pairwise_scores": {
                    "modelA_vs_modelB": float,
                    ...
                },
                "average_similarity": float,
                "min_similarity": float,
                "max_similarity": float,
                "models_compared": list[str],
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
            texts = [
                normalize_text(successful_responses[name].get("response", ""))
                for name in model_names
            ]

            # Skip if any text is empty
            if any(not text for text in texts):
                return {
                    "analyzer_name": self.analyzer_name,
                    "success": False,
                    "error": "empty_response_text",
                    "models_analyzed": model_names,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }

            # Compute embeddings
            embeddings = self.model.encode(texts, convert_to_tensor=True)

            # Compute pairwise cosine similarity
            similarity_scores: Dict[str, float] = {}
            all_similarities: list[float] = []

            for (idx_a, idx_b) in combinations(range(len(model_names)), 2):
                model_a = model_names[idx_a]
                model_b = model_names[idx_b]

                # Compute cosine similarity
                sim_score = float(util.cos_sim(embeddings[idx_a], embeddings[idx_b])[0][0])

                # Round to 4 decimals
                sim_score = round(sim_score, 4)

                key = f"{model_a}_vs_{model_b}"
                similarity_scores[key] = sim_score
                all_similarities.append(sim_score)

            # Compute statistics
            avg_similarity = round(sum(all_similarities) / len(all_similarities), 4) if all_similarities else 0.0
            min_similarity = round(min(all_similarities), 4) if all_similarities else 0.0
            max_similarity = round(max(all_similarities), 4) if all_similarities else 0.0

            return {
                "analyzer_name": self.analyzer_name,
                "success": True,
                "error": None,
                "pairwise_scores": similarity_scores,
                "average_similarity": avg_similarity,
                "min_similarity": min_similarity,
                "max_similarity": max_similarity,
                "models_compared": model_names,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

        except Exception as exc:
            return {
                "analyzer_name": self.analyzer_name,
                "success": False,
                "error": f"Analysis failed: {str(exc)}",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
