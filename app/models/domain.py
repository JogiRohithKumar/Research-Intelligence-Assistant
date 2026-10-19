"""
Domain Schemas for Research Intelligence Assistant V2.
Strict Pydantic models for domain entities across all 9 stages.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, HttpUrl


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ErrorDetail(BaseModel):
    agent: str
    error_type: str
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# -----------------------------
# User & Planning
# -----------------------------

class UserRequest(BaseModel):
    query: str = Field(..., min_length=2, description="User research question")
    session_id: Optional[str] = None
    depth: str = Field(default="comprehensive", description="Research depth level")


class SubQuestion(BaseModel):
    id: str
    question: str
    importance: str = "high"


class ResearchObjective(BaseModel):
    primary_goal: str
    scope: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    objective: Optional[ResearchObjective] = None
    sub_questions: List[SubQuestion] = Field(default_factory=list)
    planned_queries: List[str] = Field(default_factory=list)


# -----------------------------
# Search & Candidates
# -----------------------------

class SearchPlan(BaseModel):
    original_query: str
    normalized_query: str
    primary_query: str
    alternative_queries: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)
    intent: str = "scholarly_literature_review"
    retrieval_strategy: str = "hybrid_academic"
    filters: Dict[str, Any] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    query_string: str
    source: str = "arxiv"
    target_aspect: str = "general"


class CandidatePaper(BaseModel):
    id: str = Field(default="", description="Unique identifier (URL, arXiv ID, or hash)")
    title: str = Field(..., min_length=1)
    authors: List[str] = Field(default_factory=list)
    abstract: str = Field(default="")
    published: str = Field(default="")
    paper_url: str = Field(default="")
    doi: Optional[str] = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class NormalizedPaper(CandidatePaper):
    paper_id: str = Field(default="", description="Canonical unique identifier")
    year: Optional[int] = None
    source: str = Field(default="arxiv", description="Provider source (e.g. arxiv, local_corpus)")
    source_id: str = Field(default="", description="Source-specific identifier")
    journal_ref: Optional[str] = None
    citation_count: Optional[int] = None
    paper_type: str = "preprint"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ranking_explanation: str = Field(default="", description="Explainable scoring breakdown")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Retrieval source trace")

    def model_post_init(self, __context: Any) -> None:
        if not self.paper_id and self.id:
            self.paper_id = self.id
        elif not self.id and self.paper_id:
            self.id = self.paper_id


class SelectedPaper(BaseModel):
    paper: CandidatePaper
    selection_rationale: str = ""
    relevance_rank: int = 1


class SearchResults(BaseModel):
    query: str
    total_found: int = 0
    papers: List[CandidatePaper] = Field(default_factory=list)
    search_plan: Optional[SearchPlan] = None


# -----------------------------
# -----------------------------
# RAG & Evidence Grounding (Stage 3)
# -----------------------------

class RetrievedDocument(BaseModel):
    doc_id: str
    paper_id: str
    paper_title: str
    content: str
    chunk_index: int = 0
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceSourceType(str, Enum):
    INDEXED_FULL_TEXT = "indexed_full_text"
    INDEXED_ABSTRACT = "indexed_abstract"
    PROVIDER_ABSTRACT = "provider_abstract"
    LOCAL_CORPUS = "local_corpus"


class EvidenceChunk(BaseModel):
    """
    Canonical evidence representation for grounded scientific RAG.
    Contains un-paraphrased exact excerpts with full provenance.
    """
    evidence_id: str = Field(..., description="Deterministic unique evidence identifier (e.g. E001 or evidence:...)")
    paper_id: str = Field(..., description="Canonical paper identifier")
    chunk_id: str = Field(..., description="Underlying deterministic vector store chunk ID")
    text: str = Field(..., description="Exact retrieved excerpt text, never paraphrased")
    title: str = Field(..., description="Title of the source paper")
    authors: List[str] = Field(default_factory=list, description="Author full names")
    year: Optional[int] = None
    doi: Optional[str] = None
    source_url: str = Field(default="", description="Direct URL or canonical repository link")
    provider: str = Field(default="arxiv", description="Retrieval source provider")
    section: Optional[str] = None
    page: Optional[int] = None
    chunk_index: int = Field(default=0, description="Sequential index within paper chunks")
    retrieval_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Calculated retrieval similarity score")
    evidence_source_type: EvidenceSourceType = Field(
        default=EvidenceSourceType.INDEXED_ABSTRACT,
        description="Actual physical origin of evidence text"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provenance metadata")


class SupportVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None


class ClaimSupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None


class EvidenceSupportResult(BaseModel):
    """
    Structured outcome of semantic support verification for a research claim.
    Distinguishes whether the evidence actually factually substantiates the claim.
    """
    claim_id: str
    verdict: SupportVerdict
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    explanation: str = Field(default="", description="Factual justification based exclusively on evidence text")


class ClaimType(str, Enum):
    EMPIRICAL_FINDING = "empirical_finding"
    METHODOLOGICAL = "methodological"
    THEORETICAL = "theoretical"
    LIMITATION = "limitation"


class ResearchClaim(BaseModel):
    """
    Structured research claim with explicit machine-readable evidence references.
    """
    claim_id: str = Field(..., description="Unique claim identifier (e.g. C001)")
    claim_text: str = Field(..., min_length=3, description="Verbatim factual proposition")
    claim_type: ClaimType = Field(default=ClaimType.EMPIRICAL_FINDING)
    evidence_ids: List[str] = Field(default_factory=list, description="Referenced evidence chunk IDs (e.g. ['E001'])")
    support_status: ClaimSupportStatus = Field(default=ClaimSupportStatus.UNSUPPORTED)
    confidence_rationale: str = Field(default="", description="Explainable grounding rationale without fake numbers")
    source_paper_ids: List[str] = Field(default_factory=list, description="Resolved source paper identifiers")
    exact_quotes: List[str] = Field(default_factory=list, description="Direct excerpts quoted in the claim")


class CitationVerificationResult(BaseModel):
    """
    Audit record detailing claim validation, evidence mapping, and quote integrity.
    """
    total_claims: int = 0
    supported_claims: int = 0
    partially_supported_claims: int = 0
    unsupported_claims: int = 0
    total_citations: int = 0
    valid_citations: int = 0
    invalid_citations: int = 0
    quote_integrity_failures: List[Dict[str, str]] = Field(default_factory=list)
    unsupported_claim_ids: List[str] = Field(default_factory=list)
    grounding_status: str = "VERIFIED"  # "VERIFIED", "PARTIAL", "UNGROUNDED"
    notes: List[str] = Field(default_factory=list)


# Retain backwards compatibility for legacy types
Evidence = EvidenceChunk


class Claim(BaseModel):
    claim_id: str
    statement: str
    supporting_evidence: List[EvidenceChunk] = Field(default_factory=list)
    refuting_evidence: List[EvidenceChunk] = Field(default_factory=list)


# -----------------------------
# Research Intelligence (Stage 4)
# -----------------------------

class FindingType(str, Enum):
    AGREEMENT = "AGREEMENT"
    DISAGREEMENT = "DISAGREEMENT"
    CONTRADICTION = "CONTRADICTION"
    METHODOLOGY_DIFFERENCE = "METHODOLOGY_DIFFERENCE"
    EVIDENCE_GAP = "EVIDENCE_GAP"
    CONSENSUS = "CONSENSUS"
    QUALIFIED_CONCLUSION = "QUALIFIED_CONCLUSION"


class ResearchFinding(BaseModel):
    finding_id: str = Field(..., description="Unique finding ID (e.g. F001)")
    finding_text: str = Field(..., min_length=3, description="Evidence-grounded finding statement")
    finding_type: FindingType = Field(default=FindingType.AGREEMENT)
    claim_ids: List[str] = Field(default_factory=list, description="Associated claim IDs (e.g. ['C001'])")
    evidence_ids: List[str] = Field(default_factory=list, description="Direct supporting evidence IDs (e.g. ['E001'])")
    paper_ids: List[str] = Field(default_factory=list, description="Associated paper IDs")
    support_status: ClaimSupportStatus = Field(default=ClaimSupportStatus.SUPPORTED)
    explanation: str = Field(default="", description="Detailed factual explanation grounded in evidence")


class PaperComparison(BaseModel):
    """
    Structured cross-paper comparison on explicitly observed dimensions.
    Fields without evidence must remain None/null. Never inferred.
    """
    paper_id: str
    paper_title: str = ""
    research_question: Optional[str] = None
    population: Optional[str] = None
    dataset: Optional[str] = None
    sample_size: Optional[str] = None
    intervention_or_method: Optional[str] = None
    baseline_or_control: Optional[str] = None
    outcomes: Optional[str] = None
    metrics: Optional[str] = None
    evaluation_method: Optional[str] = None
    limitations: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence chunks supporting this comparison")


class ContradictionType(str, Enum):
    DIRECT_RESULT_CONFLICT = "DIRECT_RESULT_CONFLICT"
    DIRECTIONAL_CONFLICT = "DIRECTIONAL_CONFLICT"
    POPULATION_CONFLICT = "POPULATION_CONFLICT"
    METHODOLOGY_DEPENDENT = "METHODOLOGY_DEPENDENT"
    OUTCOME_DEFINITION_DIFFERENCE = "OUTCOME_DEFINITION_DIFFERENCE"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_A_CONTRADICTION = "NOT_A_CONTRADICTION"


class ContradictionFinding(BaseModel):
    """
    Explicit contradiction and disagreement representation.
    Distinguishes genuine substantive conflicts from differences in methodology, population, or dataset.
    """
    contradiction_id: str = Field(..., description="Unique identifier (e.g. CT001)")
    topic: str
    paper_a_id: str
    paper_b_id: str
    claim_a: str
    claim_b: str
    evidence_ids: List[str] = Field(default_factory=list)
    contradiction_type: ContradictionType = Field(default=ContradictionType.NOT_A_CONTRADICTION)
    possible_explanations: List[str] = Field(
        default_factory=lambda: ["UNKNOWN"],
        description="Grounded explanations for divergence; must be UNKNOWN if not supported by evidence"
    )
    is_genuine_contradiction: bool = Field(
        default=False,
        description="True ONLY if incompatible findings under comparable conditions"
    )
    support_status: ClaimSupportStatus = Field(default=ClaimSupportStatus.SUPPORTED)


class EvidenceStrengthRating(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"
    MIXED = "MIXED"
    INSUFFICIENT = "INSUFFICIENT"


class EvidenceStrength(BaseModel):
    """
    Interpretable evidence strength classification with zero fake confidence percentages.
    """
    rating: EvidenceStrengthRating = Field(default=EvidenceStrengthRating.LIMITED)
    rationale: str = Field(..., description="Verifiable explanation grounded in paper count, consistency, and directness")
    supporting_paper_count: int = 0
    contradicting_paper_count: int = 0
    evidence_chunks_count: int = 0
    consistency_assessment: str = Field(default="", description="High, moderate, mixed, or insufficient consistency")


class ResearchGapCategory(str, Enum):
    POPULATION_GAP = "POPULATION_GAP"
    DATASET_GAP = "DATASET_GAP"
    METHOD_GAP = "METHOD_GAP"
    OUTCOME_GAP = "OUTCOME_GAP"
    TIME_HORIZON_GAP = "TIME_HORIZON_GAP"
    COMPARISON_GAP = "COMPARISON_GAP"
    GENERALIZATION_GAP = "GENERALIZATION_GAP"
    EVIDENCE_GAP = "EVIDENCE_GAP"


class ResearchGapFinding(BaseModel):
    """
    Evidence-grounded research gap scoped strictly within retrieved literature.
    """
    gap_id: str = Field(..., description="Unique gap identifier (e.g. G001)")
    category: ResearchGapCategory = Field(default=ResearchGapCategory.EVIDENCE_GAP)
    description: str = Field(..., description="Factual gap description prefixed with 'Within the retrieved literature...'")
    affected_papers: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    reasoning: str = Field(default="", description="Why this constitutes a gap based on retrieved evidence patterns")


class ConsensusSynthesis(BaseModel):
    """
    Grounded consensus statement derived from validated findings.
    """
    consensus_status: str = Field(default="EMERGING", description="ESTABLISHED, EMERGING, MIXED, or INSUFFICIENT_EVIDENCE")
    synthesis_statement: str = Field(..., description="Collective finding narrative grounded in evidence")
    divergent_points: List[str] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    supporting_evidence_ids: List[str] = Field(default_factory=list)


class ResearchIntelligenceReport(BaseModel):
    """
    Complete Stage 4 Research Intelligence package with full provenance audit.
    """
    findings: List[ResearchFinding] = Field(default_factory=list)
    comparisons: List[PaperComparison] = Field(default_factory=list)
    contradictions: List[ContradictionFinding] = Field(default_factory=list)
    gaps: List[ResearchGapFinding] = Field(default_factory=list)
    consensus: Optional[ConsensusSynthesis] = None
    evidence_strength: Optional[EvidenceStrength] = None
    provenance_audit: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------
# Agentic Research Loop (Stage 5)
# -----------------------------

class SufficiencyStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTED = "CONFLICTED"
    NO_RELIABLE_EVIDENCE = "NO_RELIABLE_EVIDENCE"


class EvidenceSufficiency(BaseModel):
    """
    Structured outcome of evidence sufficiency evaluation.
    Qualitative evaluation based strictly on empirical counts, contradictions, and gaps.
    """
    status: SufficiencyStatus
    rationale: str
    paper_count: int = 0
    evidence_chunk_count: int = 0
    supported_claim_count: int = 0
    unsupported_claim_count: int = 0
    is_concentrated_in_single_paper: bool = False
    has_unresolved_contradictions: bool = False
    unanswered_subquestions: List[str] = Field(default_factory=list)
    is_additional_research_warranted: bool = False


class ResearchStopReason(str, Enum):
    EVIDENCE_SUFFICIENT = "EVIDENCE_SUFFICIENT"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    NO_ACTIONABLE_GAPS = "NO_ACTIONABLE_GAPS"
    NO_PROGRESS = "NO_PROGRESS"
    REPEATED_QUERIES = "REPEATED_QUERIES"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    PROVIDER_EXHAUSTION = "PROVIDER_EXHAUSTION"


class ResearchAction(str, Enum):
    CONTINUE_RESEARCH = "CONTINUE_RESEARCH"
    STOP_RESEARCH = "STOP_RESEARCH"


class ActionableResearchGap(BaseModel):
    """
    A grounded, actionable gap identified during research that can be targeted in follow-up iterations.
    """
    gap_id: str = Field(default_factory=lambda: f"GAP_{uuid.uuid4().hex[:6]}")
    title: str = ""
    description: str
    category: str = "EVIDENCE_GAP"  # POPULATION_GAP, DATASET_GAP, METHOD_GAP, OUTCOME_GAP, etc.
    impact: str = "high"
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW
    evidence_ids: List[str] = Field(default_factory=list)
    affected_papers: List[str] = Field(default_factory=list)
    recommended_research_action: str = ""


# Enhance ResearchGap to be backwards-compatible with legacy while supporting Stage 5 ActionableResearchGap
ResearchGap = ActionableResearchGap


class TargetedResearchQuery(BaseModel):
    """
    Structured query generated to resolve a specific research gap in an iteration.
    """
    query_id: str
    parent_query: str
    gap_addressed_id: str
    query_text: str
    rationale: str
    target_concepts: List[str] = Field(default_factory=list)
    strategy: str = "EVIDENCE_GAP"
    iteration: int = 1


class ResearchDecision(BaseModel):
    """
    Decision point on whether to continue research loop or finalize report.
    """
    action: ResearchAction
    stop_reason: Optional[ResearchStopReason] = None
    sufficiency: EvidenceSufficiency
    selected_gap: Optional[ActionableResearchGap] = None
    rationale: str = ""


class ResearchIteration(BaseModel):
    """
    Detailed audit log of an individual agentic research loop iteration.
    """
    iteration_id: int
    parent_iteration_id: Optional[int] = None
    query_used: str
    search_plan: Optional[Dict[str, Any]] = None
    retrieved_paper_ids: List[str] = Field(default_factory=list)
    new_paper_count: int = 0
    cumulative_paper_count: int = 0
    retrieved_evidence_ids: List[str] = Field(default_factory=list)
    new_evidence_count: int = 0
    cumulative_evidence_count: int = 0
    supported_claims_count: int = 0
    partially_supported_claims_count: int = 0
    unsupported_claims_count: int = 0
    research_findings_count: int = 0
    detected_gaps: List[str] = Field(default_factory=list)
    decision: ResearchDecision
    stop_reason: Optional[ResearchStopReason] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ResearchLoopState(BaseModel):
    """
    Complete state of the agentic research loop across iterations.
    """
    current_iteration: int = 1
    max_iterations: int = 3
    iterations: List[ResearchIteration] = Field(default_factory=list)
    executed_queries: List[str] = Field(default_factory=list)
    executed_gap_ids: List[str] = Field(default_factory=list)
    cumulative_paper_ids: List[str] = Field(default_factory=list)
    cumulative_evidence_ids: List[str] = Field(default_factory=list)
    total_search_calls: int = 0
    consecutive_no_progress_count: int = 0
    final_stop_reason: Optional[ResearchStopReason] = None
    active_targeted_query: Optional[TargetedResearchQuery] = None


# -----------------------------
# Legacy Compatibility Models
# -----------------------------

class VerificationFinding(BaseModel):
    finding: str
    status: str = "supported"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    supporting_paper_ids: List[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    common_findings: List[str] = Field(default_factory=list)
    conflicting_findings: List[str] = Field(default_factory=list)
    evidence_strength: str = Field(default="moderate")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ComparisonRow(BaseModel):
    paper_title: str
    methodology: str
    sample_size: Optional[str] = None
    key_metric: Optional[str] = None
    outcome: str


class StudyComparison(BaseModel):
    dimension: str
    rows: List[ComparisonRow] = Field(default_factory=list)


class Contradiction(BaseModel):
    topic: str
    claim_a: str
    claim_b: str
    source_a: str
    source_b: str
    explanation: str


class GapAnalysisResult(BaseModel):
    research_gaps: List[str] = Field(default_factory=list)
    missing_areas: List[str] = Field(default_factory=list)
    future_directions: List[str] = Field(default_factory=list)
    unanswered_questions: List[str] = Field(default_factory=list)


class Consensus(BaseModel):
    agreement_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    consensus_summary: str = ""
    divergent_points: List[str] = Field(default_factory=list)


# -----------------------------
# Citations & Reporting
# -----------------------------

class CitationItem(BaseModel):
    title: str
    apa: str
    ieee: str
    mla: str
    bibtex: str


class FinalReport(BaseModel):
    query: str
    executive_summary: str
    common_findings: List[str] = Field(default_factory=list)
    conflicting_findings: List[str] = Field(default_factory=list)
    evidence_strength: str = "moderate"
    confidence_score: float = 0.0
    research_gaps: List[str] = Field(default_factory=list)
    missing_areas: List[str] = Field(default_factory=list)
    future_directions: List[str] = Field(default_factory=list)
    unanswered_questions: List[str] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)
    markdown_content: str = ""


# -----------------------------
# Observability & Trace
# -----------------------------

class AgentLog(BaseModel):
    agent: str
    status: str
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None


class ResearchTrace(BaseModel):
    steps: List[AgentLog] = Field(default_factory=list)
