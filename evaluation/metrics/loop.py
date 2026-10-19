"""
Stage 5 Agentic Research Loop Metrics.
Evaluates iterative efficiency, stopping condition adherence, and query drift prevention.
"""

from typing import List


def calculate_loop_efficiency(iterations_count: int, evidence_gain_history: List[int]) -> float:
    """
    Evaluates whether subsequent iterations added meaningful evidence.
    Penalizes loops that continued running despite zero new evidence gain.
    """
    if iterations_count <= 1:
        return 1.0  # Single iteration with valid evidence is efficient

    if not evidence_gain_history:
        return 0.5

    # Check for empty iterations
    empty_iterations = sum(1 for gain in evidence_gain_history if gain <= 0)
    penalty = (empty_iterations / len(evidence_gain_history)) * 0.5
    efficiency = max(0.0, 1.0 - penalty)
    return round(efficiency, 4)


def verify_stopping_reason(actual_reason: str, valid_reasons: List[str]) -> bool:
    """
    Verifies that the loop terminated for an authorized, expected stopping criterion:
    EVIDENCE_SUFFICIENT, MAX_ITERATIONS_REACHED, NO_PROGRESS, NO_ACTIONABLE_GAPS,
    REPEATED_QUERIES, BUDGET_EXHAUSTED, PROVIDER_EXHAUSTION.
    """
    actual_norm = actual_reason.upper().strip()
    valid_norms = [v.upper().strip() for v in valid_reasons]
    return actual_norm in valid_norms


def detect_query_drift(initial_query: str, subsequent_queries: List[str]) -> bool:
    """
    Detects if targeted queries have drifted off-topic from the original research question.
    Returns True if query drift is detected.
    """
    if not subsequent_queries:
        return False

    core_tokens = {w.lower() for w in initial_query.split() if len(w) > 3}
    for q in subsequent_queries:
        q_tokens = {w.lower() for w in q.split() if len(w) > 3}
        # If there is zero overlap with core tokens or related synonyms, flag drift
        if not core_tokens.intersection(q_tokens):
            return True
    return False
