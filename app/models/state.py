"""
Authoritative State Definitions for Research Intelligence Assistant V2.
Bridges LangGraph StateGraph with strict Pydantic domain models.
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict
import operator

from pydantic import BaseModel, Field

from app.models.domain import (
    CandidatePaper,
    CitationItem,
    ErrorDetail,
    ExecutionStatus,
    FinalReport,
    GapAnalysisResult,
    VerificationResult,
)


# -----------------------------
# LLM Structured Output Schemas
# -----------------------------

class SupervisorDecision(BaseModel):
    status: str = Field(..., description="'valid' for academic query, 'invalid' for non-research, 'retry' if refinement needed")
    reason: str = Field(default="", description="Explanation of decision")
    modified_query: str = Field(default="", description="Refined query if status is retry or needs optimization")
    route: str = Field(default="continue", description="'continue' to search, 'stop' to end, 'retry_search' to retry")


class PaperSummary(BaseModel):
    title: str = Field(..., description="Title of the paper")
    summary: str = Field(..., description="2-3 sentence concise summary")
    key_findings: List[str] = Field(default_factory=list, description="Key research findings")


class PaperSummaryList(BaseModel):
    summaries: List[PaperSummary] = Field(default_factory=list)


class QueryOptimizationResult(BaseModel):
    optimized_query: str = Field(..., description="Refined search query under 15 words")
    keywords: List[str] = Field(default_factory=list, description="Important academic keywords")


# -----------------------------
# LangGraph Authoritative State
# -----------------------------

class ResearchState(TypedDict):
    """
    Authoritative state for LangGraph pipeline.
    All fields are explicitly typed to avoid untyped dictionary chaos.
    """
    # Session & Query Context
    thread_id: str
    query: str
    retry_count: int
    execution_status: str

    # Pipeline Artifacts
    supervisor: Optional[Dict[str, Any]]
    search_plan: Optional[Dict[str, Any]]
    papers: List[Dict[str, Any]]
    retrieved_documents: List[Dict[str, Any]]
    evidence_registry: List[Dict[str, Any]]
    claims: List[Dict[str, Any]]
    grounded_summary: str
    citation_verification: Optional[Dict[str, Any]]
    grounding_status: str
    summaries: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    verification: Optional[Dict[str, Any]]
    gaps: Optional[Dict[str, Any]]
    intelligence: Optional[Dict[str, Any]]
    
    # Stage 4 Research Intelligence State
    cross_paper_findings: Optional[List[Dict[str, Any]]]
    study_comparisons: Optional[List[Dict[str, Any]]]
    contradiction_findings: Optional[List[Dict[str, Any]]]
    evidence_strength: Optional[Dict[str, Any]]
    research_gaps: Optional[List[Dict[str, Any]]]
    consensus_synthesis: Optional[Dict[str, Any]]
    
    # Stage 5 Agentic Research Loop State
    current_iteration: int
    max_iterations: int
    loop_state: Optional[Dict[str, Any]]
    active_targeted_query: Optional[Dict[str, Any]]
    sufficiency_evaluation: Optional[Dict[str, Any]]
    actionable_gaps: Optional[List[Dict[str, Any]]]
    research_decision: Optional[Dict[str, Any]]
    iterations_history: Optional[List[Dict[str, Any]]]

    report: str
    final_report: Optional[Dict[str, Any]]

    # Observability & Trace Reducers
    agent_logs: Annotated[List[Dict[str, Any]], operator.add]
    errors: Annotated[List[Dict[str, Any]], operator.add]
