"""
Typed Models for Stage 8 Evaluation Framework.
Provides immutable Pydantic schemas for test cases, datasets, metrics, and run records.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from evaluation.taxonomy import EvaluationDimension, FailureCategory, EvaluationVerdict, QualityGateType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReferenceEvidence(BaseModel):
    """Reference evidence snippet with provenance metadata."""
    evidence_id: str
    paper_title: str
    source_url: Optional[str] = None
    doi: Optional[str] = None
    text_snippet: str
    is_relevant: bool = True
    section: Optional[str] = None


class ReferenceClaim(BaseModel):
    """Reference claim with expected grounding verdict and citing evidence."""
    claim_id: str
    claim_text: str
    expected_status: str  # SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, INSUFFICIENT_EVIDENCE
    supported_by_ids: List[str] = Field(default_factory=list)
    contains_causal_overreach: bool = False
    contains_population_mismatch: bool = False


class EvaluationCase(BaseModel):
    """Standardized evaluation case specification."""
    model_config = ConfigDict(frozen=True)

    case_id: str
    name: str
    dimension: EvaluationDimension
    research_question: str
    expected_behavior: str
    expected_verdict: Optional[str] = None
    reference_evidence: List[ReferenceEvidence] = Field(default_factory=list)
    reference_claims: List[ReferenceClaim] = Field(default_factory=list)
    failure_criteria: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationDataset(BaseModel):
    """Versioned collection of research evaluation cases."""
    dataset_id: str
    version: str
    description: str
    cases: List[EvaluationCase]
    created_at: datetime = Field(default_factory=utc_now)


class MetricResult(BaseModel):
    """Calculated metric output with threshold compliance check."""
    metric_name: str
    dimension: EvaluationDimension
    value: float
    threshold: Optional[float] = None
    unit: str = "ratio"
    passed: bool = True
    gate_type: QualityGateType = QualityGateType.INFORMATIONAL
    rationale: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class QualityGate(BaseModel):
    """Quality gate standard used to certify release readiness."""
    gate_id: str
    name: str
    dimension: EvaluationDimension
    metric_name: str
    calculation: str
    minimum_threshold: float
    rationale: str
    gate_type: QualityGateType = QualityGateType.HARD


class EvaluationResult(BaseModel):
    """Evaluation outcome for an individual test case."""
    case_id: str
    case_name: str
    dimension: EvaluationDimension
    passed: bool
    failures: List[FailureCategory] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class EvaluationRun(BaseModel):
    """Immutable record of an executed evaluation run."""
    run_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    code_version: str = "1.0.0"
    dataset_version: str = "1.0.0"
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    case_results: List[EvaluationResult] = Field(default_factory=list)
    metric_results: List[MetricResult] = Field(default_factory=list)
    gate_results: Dict[str, Any] = Field(default_factory=dict)
    failures_by_category: Dict[str, int] = Field(default_factory=dict)
    duration_seconds: float = 0.0
    final_verdict: EvaluationVerdict = EvaluationVerdict.HOLD
    environment: Dict[str, str] = Field(default_factory=dict)
