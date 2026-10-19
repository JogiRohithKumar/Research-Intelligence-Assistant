"""
Failure Taxonomy and Evaluation Enums for Stage 8.
Defines stable categories, evaluation dimensions, and quality gate types.
"""

from enum import Enum


class EvaluationDimension(str, Enum):
    """Core evaluation dimensions across Research Intelligence Assistant pipeline."""
    RETRIEVAL = "retrieval"
    EVIDENCE_RAG = "evidence_rag"
    CLAIMS_CITATIONS = "claims_citations"
    RESEARCH_INTELLIGENCE = "research_intelligence"
    AGENTIC_LOOP = "agentic_loop"
    ADVERSARIAL = "adversarial"
    SECURITY_REGRESSION = "security_regression"
    PERFORMANCE = "performance"


class FailureCategory(str, Enum):
    """Stable failure categorization taxonomy for research assistant evaluation."""
    # Retrieval Failures
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    IRRELEVANT_RETRIEVAL = "IRRELEVANT_RETRIEVAL"
    DUPLICATE_RETRIEVAL = "DUPLICATE_RETRIEVAL"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"

    # Evidence & Grounding Failures
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
    CITATION_MISMATCH = "CITATION_MISMATCH"
    FABRICATED_QUOTE = "FABRICATED_QUOTE"
    SOURCE_MISMATCH = "SOURCE_MISMATCH"

    # Reasoning & Overreach Failures
    CAUSAL_OVERREACH = "CAUSAL_OVERREACH"
    POPULATION_MISMATCH = "POPULATION_MISMATCH"
    OUTCOME_MISMATCH = "OUTCOME_MISMATCH"
    QUANTITATIVE_MISMATCH = "QUANTITATIVE_MISMATCH"
    SUPERLATIVE_OVERCLAIM = "SUPERLATIVE_OVERCLAIM"

    # Research Intelligence Failures
    CONTRADICTION_MISCLASSIFICATION = "CONTRADICTION_MISCLASSIFICATION"
    GAP_OVERCLAIM = "GAP_OVERCLAIM"
    CONSENSUS_OVERCLAIM = "CONSENSUS_OVERCLAIM"

    # Agentic Loop Failures
    QUERY_DRIFT = "QUERY_DRIFT"
    LOOP_NO_PROGRESS = "LOOP_NO_PROGRESS"
    LOOP_OVERSEARCH = "LOOP_OVERSEARCH"
    REPEATED_QUERY = "REPEATED_QUERY"

    # System & Security Failures
    STRUCTURED_OUTPUT_FAILURE = "STRUCTURED_OUTPUT_FAILURE"
    PERSISTENCE_FAILURE = "PERSISTENCE_FAILURE"
    SECURITY_REGRESSION = "SECURITY_REGRESSION"
    MALFORMED_INPUT = "MALFORMED_INPUT"


class EvaluationVerdict(str, Enum):
    """Terminal verdict for an evaluation case or full run."""
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    HOLD = "HOLD"


class QualityGateType(str, Enum):
    """Distinguishes mandatory pass/fail criteria from observational benchmarks."""
    HARD = "HARD"
    INFORMATIONAL = "INFORMATIONAL"
