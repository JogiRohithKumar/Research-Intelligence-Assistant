"""
Metric implementations for Stage 8 evaluation.
Provides deterministic, mathematically sound evaluation calculations.
"""

from evaluation.metrics.retrieval import (
    calculate_recall_at_k,
    calculate_precision_at_k,
    calculate_hit_at_k,
    calculate_mrr,
    calculate_duplicate_rate,
)
from evaluation.metrics.evidence_rag import (
    calculate_evidence_relevance,
    calculate_provenance_completeness,
    calculate_evidence_sufficiency,
)
from evaluation.metrics.claims_citations import (
    calculate_citation_validity,
    calculate_claim_grounding_accuracy,
    detect_causal_overreach,
)
from evaluation.metrics.intelligence import (
    calculate_contradiction_precision,
    calculate_gap_qualification_rate,
    verify_evidence_strength_heuristic,
)
from evaluation.metrics.loop import (
    calculate_loop_efficiency,
    verify_stopping_reason,
    detect_query_drift,
)

__all__ = [
    "calculate_recall_at_k",
    "calculate_precision_at_k",
    "calculate_hit_at_k",
    "calculate_mrr",
    "calculate_duplicate_rate",
    "calculate_evidence_relevance",
    "calculate_provenance_completeness",
    "calculate_evidence_sufficiency",
    "calculate_citation_validity",
    "calculate_claim_grounding_accuracy",
    "detect_causal_overreach",
    "calculate_contradiction_precision",
    "calculate_gap_qualification_rate",
    "verify_evidence_strength_heuristic",
    "calculate_loop_efficiency",
    "verify_stopping_reason",
    "detect_query_drift",
]
