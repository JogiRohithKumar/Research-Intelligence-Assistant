"""
Authoritative Research Graph for Research Intelligence Assistant V2.
Constructs and compiles the StateGraph pipeline with typed state,
explicit error handling, and robust routing.
"""

import time
from typing import Any, Dict, List
from langgraph.graph import StateGraph, START, END

from app.db.checkpoint import checkpointer
from app.memory.memory_manager import save_session

from app.agents.search_agent import get_search_engine, search_papers
from app.agents.summary_agent import summarize_papers
from app.agents.citation_agent import generate_citations
from app.agents.research_intelligence_agent import generate_research_intelligence
from app.agents.report_agent import generate_report
from app.agents.supervisor_agent import generate_supervisor_decision
from app.agents.grounded_synthesis_agent import synthesize_grounded_research

from app.core.config import get_settings
from app.core.logging import logger
from app.models.state import ResearchState
from app.utils.safe_execute import safe_execute
from app.utils.stream_logger import stream_log, clear_stream_events, emit_lifecycle_event
from app.rag.vector_store import store_papers
from app.rag.retriever import retrieve_context
from app.rag.evidence import EvidenceRegistry
from app.rag.evidence_retriever import EvidenceRetriever
from app.loop import (
    EvidenceSufficiencyEvaluator,
    ActionableGapAnalyzer,
    TargetedQueryPlanner,
    ResearchLoopController,
)
from app.models.domain import (
    ActionableResearchGap,
    EvidenceSufficiency,
    ResearchAction,
    ResearchDecision,
    ResearchIteration,
    ResearchLoopState,
    ResearchStopReason,
    SufficiencyStatus,
    TargetedResearchQuery,
)


# -----------------------------
# SUPERVISOR NODE & ROUTER
# -----------------------------

def supervisor_node(state: ResearchState) -> Dict[str, Any]:
    """Evaluates the query and determines whether to proceed, refine, or stop."""
    query = state.get("query", "")
    retry_count = state.get("retry_count", 0)

    result = safe_execute(
        "Supervisor Agent",
        generate_supervisor_decision,
        query
    )

    if not result["success"]:
        return {
            "supervisor": {
                "status": "valid",
                "route": "continue",
                "reason": "Proceeding with default validation"
            },
            "execution_status": "in_progress",
            "errors": [{
                "agent": "supervisor",
                "error_type": "SupervisorExecutionWarning",
                "message": str(result["error"])
            }]
        }

    decision = result["result"]
    updates: Dict[str, Any] = {
        "supervisor": decision,
        "execution_status": "in_progress",
        "agent_logs": [{
            "agent": "supervisor",
            "status": "success",
            "message": f"Query evaluated: status={decision.get('status')}"
        }]
    }

    # If supervisor proposed an improved modified query, apply it
    modified_query = decision.get("modified_query", "").strip()
    if decision.get("status") == "retry" and modified_query and retry_count < 2:
        updates["query"] = modified_query
        updates["retry_count"] = retry_count + 1
        stream_log(f"Supervisor refined query to: '{modified_query}'")

    return updates


def supervisor_router(state: ResearchState) -> str:
    """Explicit conditional routing based on supervisor evaluation."""
    decision = state.get("supervisor", {})
    status = decision.get("status", "valid")

    if status == "invalid":
        logger.info("Supervisor rejected query as non-research; routing to END")
        return END

    return "search"


# -----------------------------
# SEARCH NODE & ROUTER
# -----------------------------

def search_node(state: ResearchState) -> Dict[str, Any]:
    """Retrieves candidate scientific papers using Stage 2 ResearchSearchEngine with Stage 5 deduplication and accretion."""
    clear_stream_events()
    query = state.get("query", "")
    existing_papers = state.get("papers", [])
    current_iteration = state.get("current_iteration", 1)

    emit_lifecycle_event("iteration_started", {"iteration": current_iteration, "query": query})
    emit_lifecycle_event("search_started", {"iteration": current_iteration, "query": query})

    engine = get_search_engine()
    result = safe_execute(
        "Search Engine",
        engine.search,
        query
    )

    if not result["success"]:
        if current_iteration > 1 and existing_papers:
            logger.warning(f"Targeted search failed on iteration {current_iteration}: {result['error']}. Proceeding with existing papers.")
            return {
                "papers": existing_papers,
                "agent_logs": [{
                    "agent": "search",
                    "status": "warning",
                    "message": f"Iteration {current_iteration} search failed; continuing with {len(existing_papers)} existing papers"
                }]
            }
        return {
            "papers": [],
            "search_plan": None,
            "execution_status": "failed",
            "errors": [{
                "agent": "search",
                "error_type": "SearchExecutionError",
                "message": str(result["error"])
            }],
            "agent_logs": [{
                "agent": "search",
                "status": "failed",
                "error": str(result["error"])
            }]
        }

    search_output = result["result"] or {}
    new_candidate_papers = [
        p.model_dump() if hasattr(p, "model_dump") else p
        for p in search_output.get("papers", [])
    ]
    plan = search_output.get("plan")
    plan_dict = plan.model_dump() if hasattr(plan, "model_dump") else plan
    telemetry = search_output.get("telemetry", {})

    # Deduplicate against existing papers
    existing_pids = {str(p.get("paper_id") or p.get("id")) for p in existing_papers if (p.get("paper_id") or p.get("id"))}
    new_unique = [p for p in new_candidate_papers if str(p.get("paper_id") or p.get("id")) not in existing_pids]
    cumulative_papers = existing_papers + new_unique if existing_papers else new_candidate_papers

    stream_log(f"Search Engine Completed: Retrieved {len(new_candidate_papers)} papers ({len(new_unique)} new unique, cumulative={len(cumulative_papers)})")
    emit_lifecycle_event("search_completed", {
        "papers_count": len(cumulative_papers),
        "new_papers_count": len(new_unique),
        "iteration": current_iteration
    })

    return {
        "papers": cumulative_papers,
        "search_plan": plan_dict,
        "agent_logs": [{
            "agent": "search",
            "status": "success",
            "message": (
                f"Retrieved {len(new_candidate_papers)} papers ({len(new_unique)} new, cumulative={len(cumulative_papers)}) "
                f"(variants={telemetry.get('variants_executed', 1)}, "
                f"dedup_removed={telemetry.get('duplicates_removed', 0)})"
            )
        }]
    }


def search_router(state: ResearchState) -> str:
    """Terminates graph if no papers could be retrieved."""
    papers = state.get("papers", [])
    if not papers:
        logger.warning("No papers retrieved; routing to END")
        return END

    return "rag"


# -----------------------------
# RAG INGESTION & EVIDENCE RETRIEVAL NODE (Stage 3)
# -----------------------------

def rag_node(state: ResearchState) -> Dict[str, Any]:
    """
    Ingests retrieved papers into vector storage with deterministic upsert,
    and performs evidence-first retrieval to construct the session EvidenceRegistry.
    Preserves evidence chunks across loop iterations.
    """
    papers = state.get("papers", [])
    query = state.get("query", "")
    thread_id = state.get("thread_id", "default_thread")
    existing_registry_data = state.get("evidence_registry", [])

    # 1. Deterministic storage / upsert
    store_result = safe_execute(
        "RAG Store",
        store_papers,
        papers
    )

    # 2. Evidence-First Retrieval with session isolation and accretion across iterations
    ev_retriever = EvidenceRetriever()
    existing_registry = EvidenceRegistry.from_list(existing_registry_data, run_id=thread_id) if existing_registry_data else None

    ev_result = safe_execute(
        "Evidence Retriever",
        ev_retriever.retrieve_evidence,
        query,
        papers,
        None,  # top_k
        None,  # min_similarity
        thread_id,
        existing_registry
    )

    registry = ev_result["result"] if ev_result["success"] and ev_result["result"] else (existing_registry or EvidenceRegistry(run_id=thread_id))
    evidence_list = registry.to_list()

    # Also capture raw vector context
    retrieval_result = safe_execute(
        "RAG Retrieve",
        retrieve_context,
        query
    )
    retrieved_docs: List[Dict[str, Any]] = list(state.get("retrieved_documents", []))
    if retrieval_result["success"] and retrieval_result["result"]:
        new_docs = [
            doc.model_dump() if hasattr(doc, "model_dump") else doc
            for doc in retrieval_result["result"]
        ]
        seen_doc_ids = {d.get("doc_id") for d in retrieved_docs if d.get("doc_id")}
        for nd in new_docs:
            if nd.get("doc_id") not in seen_doc_ids:
                retrieved_docs.append(nd)

    stream_log(f"RAG Evidence Registry Built: {len(evidence_list)} verified evidence chunks")
    emit_lifecycle_event("evidence_retrieval", {
        "evidence_count": len(evidence_list),
        "documents_count": len(retrieved_docs)
    })

    updates: Dict[str, Any] = {
        "evidence_registry": evidence_list,
        "retrieved_documents": retrieved_docs,
        "agent_logs": [{
            "agent": "rag",
            "status": "success",
            "message": f"Ingested {len(papers)} papers; retrieved {len(evidence_list)} evidence chunks into registry"
        }]
    }

    if not store_result["success"]:
        updates["errors"] = [{
            "agent": "rag",
            "error_type": "RAGIngestionWarning",
            "message": str(store_result["error"])
        }]

    return updates


# -----------------------------
# GROUNDED SYNTHESIS NODE (Stage 3)
# -----------------------------

def summary_node(state: ResearchState) -> Dict[str, Any]:
    """
    Synthesizes evidence-grounded research claims mapped to EvidenceChunk IDs.
    Validates claim grounding and quote integrity.
    """
    papers = state.get("papers", [])
    query = state.get("query", "")
    thread_id = state.get("thread_id", "default_thread")
    evidence_data = state.get("evidence_registry", [])

    registry = EvidenceRegistry.from_list(evidence_data, run_id=thread_id)

    # 1. Grounded synthesis: Claims -> Evidence mapping & verification
    synthesis_res = safe_execute(
        "Grounded Synthesis",
        synthesize_grounded_research,
        query,
        registry
    )

    synthesis_output = synthesis_res["result"] if synthesis_res["success"] and synthesis_res["result"] else {}
    claims = synthesis_output.get("claims", [])
    grounded_summary = synthesis_output.get("grounded_summary", "")
    verification_data = synthesis_output.get("verification", {})
    grounding_status = verification_data.get("grounding_status", "UNGROUNDED")

    # 2. Structured per-paper summaries for downstream compatibility
    summary_res = safe_execute(
        "Summary Agent",
        summarize_papers,
        papers
    )
    summaries = summary_res["result"] or []

    stream_log(f"Grounded Synthesis Completed: {len(claims)} claims generated (Status: {grounding_status})")

    updates: Dict[str, Any] = {
        "claims": claims,
        "grounded_summary": grounded_summary,
        "citation_verification": verification_data,
        "grounding_status": grounding_status,
        "summaries": summaries,
        "agent_logs": [{
            "agent": "summary",
            "status": "success",
            "message": f"Generated {len(claims)} grounded claims (Status: {grounding_status})"
        }]
    }

    if not synthesis_res["success"]:
        updates["errors"] = [{
            "agent": "summary",
            "error_type": "GroundedSynthesisWarning",
            "message": str(synthesis_res["error"])
        }]

    return updates


def summary_router(state: ResearchState) -> str:
    """Terminates pipeline if summarization yielded no usable content."""
    summaries = state.get("summaries", [])
    if not summaries:
        return END

    return "citation"


# -----------------------------
# CITATION NODE
# -----------------------------

def citation_node(state: ResearchState) -> Dict[str, Any]:
    """Generates formatted academic citations in APA, IEEE, MLA, and BibTeX."""
    papers = state.get("papers", [])

    result = safe_execute(
        "Citation Agent",
        generate_citations,
        papers
    )

    if not result["success"]:
        return {
            "citations": [],
            "errors": [{
                "agent": "citation",
                "error_type": "CitationExecutionError",
                "message": str(result["error"])
            }],
            "agent_logs": [{
                "agent": "citation",
                "status": "failed",
                "error": str(result["error"])
            }]
        }

    citations = result["result"] or []
    stream_log("Citation Agent Completed")

    return {
        "citations": citations,
        "agent_logs": [{
            "agent": "citation",
            "status": "success",
            "message": f"Generated citations for {len(citations)} papers"
        }]
    }


# -----------------------------
# RESEARCH INTELLIGENCE NODE
# -----------------------------

def intelligence_node(state: ResearchState) -> Dict[str, Any]:
    """Orchestrates Stage 4 research intelligence: cross-paper analysis, contradictions, gaps, and consensus."""
    query = state.get("query", "")
    summaries = state.get("summaries", [])
    citations = state.get("citations", [])
    papers = state.get("papers", [])
    evidence_registry = state.get("evidence_registry", [])
    claims = state.get("claims", [])

    result = safe_execute(
        "Research Intelligence Agent",
        generate_research_intelligence,
        query,
        summaries,
        citations,
        papers,
        evidence_registry,
        claims,
    )

    if not result["success"]:
        return {
            "intelligence": {},
            "cross_paper_findings": [],
            "study_comparisons": [],
            "contradiction_findings": [],
            "evidence_strength": None,
            "research_gaps": [],
            "consensus_synthesis": None,
            "errors": [{
                "agent": "intelligence",
                "error_type": "IntelligenceExecutionError",
                "message": str(result["error"])
            }],
            "agent_logs": [{
                "agent": "intelligence",
                "status": "failed",
                "error": str(result["error"])
            }]
        }

    intelligence = result["result"] or {}
    stream_log("Research Intelligence Completed")
    emit_lifecycle_event("intelligence", {
        "findings_count": len(intelligence.get("findings", [])),
        "comparisons_count": len(intelligence.get("comparisons", [])),
        "contradictions_count": len(intelligence.get("contradictions", [])),
        "strength": intelligence.get("evidence_strength", {}).get("rating", "UNKNOWN")
    })

    return {
        "intelligence": intelligence,
        "verification": intelligence.get("verification"),
        "gaps": intelligence.get("legacy_gaps") or intelligence.get("gaps"),
        "cross_paper_findings": intelligence.get("findings", []),
        "study_comparisons": intelligence.get("comparisons", []),
        "contradiction_findings": intelligence.get("contradictions", []),
        "evidence_strength": intelligence.get("evidence_strength"),
        "research_gaps": intelligence.get("gaps", []),
        "consensus_synthesis": intelligence.get("consensus"),
        "agent_logs": [{
            "agent": "intelligence",
            "status": "success",
            "message": (
                f"Synthesized Stage 4 research intelligence: {len(intelligence.get('findings', []))} findings, "
                f"{len(intelligence.get('comparisons', []))} comparisons, {len(intelligence.get('contradictions', []))} contradictions, "
                f"strength={intelligence.get('evidence_strength', {}).get('rating', 'UNKNOWN')}"
            )
        }]
    }


# -----------------------------
# EVIDENCE SUFFICIENCY & LOOP CONTROLLER NODE (Stage 5)
# -----------------------------

_loop_controller = ResearchLoopController()


def sufficiency_node(state: ResearchState) -> Dict[str, Any]:
    """
    Evaluates evidence completeness, unsupported claims, contradictions, and gaps.
    Decides whether to perform another targeted research iteration or finalize the report.
    """
    settings = get_settings()
    query = state.get("query", "")
    loop_state_dict = state.get("loop_state")

    if loop_state_dict:
        loop_state = ResearchLoopState(**loop_state_dict)
    else:
        loop_state = _loop_controller.initialize_state(
            initial_query=query,
            max_iterations=state.get("max_iterations") or settings.MAX_RESEARCH_LOOP_ITERATIONS
        )

    # Check feature flag
    if not settings.ENABLE_AGENTIC_LOOP:
        logger.info("Agentic research loop disabled via configuration; stopping research.")
        decision = ResearchDecision(
            action=ResearchAction.STOP_RESEARCH,
            stop_reason=ResearchStopReason.EVIDENCE_SUFFICIENT,
            sufficiency=EvidenceSufficiency(
                status=SufficiencyStatus.SUFFICIENT,
                rationale="Agentic loop disabled via configuration; single-pass completion.",
                paper_count=len(state.get("papers", [])),
                evidence_chunk_count=len(state.get("evidence_registry", []))
            ),
            rationale="Agentic research loop disabled."
        )
        return {
            "loop_state": loop_state.model_dump(),
            "research_decision": decision.model_dump(),
            "agent_logs": [{
                "agent": "sufficiency",
                "status": "success",
                "message": "Loop disabled; finalizing research."
            }]
        }

    start_time = time.time()
    papers = state.get("papers", [])
    evidence_registry = state.get("evidence_registry", [])
    claims = state.get("claims", [])
    intelligence = state.get("intelligence", {})
    search_plan = state.get("search_plan")
    thread_id = state.get("thread_id", "default_thread")

    original_query = loop_state.executed_queries[0] if loop_state.executed_queries else query

    sufficiency, decision, actionable_gaps, updated_loop_state = _loop_controller.evaluate_and_record_iteration(
        query=original_query,
        search_plan=search_plan,
        papers=papers,
        evidence_registry=evidence_registry,
        claims=claims,
        intelligence=intelligence,
        loop_state=loop_state,
        session_id=thread_id,
        start_time=start_time
    )

    stream_log(
        f"Sufficiency Evaluated: status={sufficiency.status.value}, "
        f"action={decision.action.value}, "
        f"stop_reason={decision.stop_reason.value if decision.stop_reason else 'NONE'}"
    )
    emit_lifecycle_event("sufficiency", {
        "status": sufficiency.status.value,
        "action": decision.action.value,
        "stop_reason": decision.stop_reason.value if decision.stop_reason else None,
        "iteration": updated_loop_state.current_iteration
    })
    emit_lifecycle_event("iteration_completed", {
        "iteration": updated_loop_state.current_iteration,
        "status": sufficiency.status.value,
        "action": decision.action.value
    })

    return {
        "loop_state": updated_loop_state.model_dump(),
        "current_iteration": updated_loop_state.current_iteration,
        "sufficiency_evaluation": sufficiency.model_dump(),
        "research_decision": decision.model_dump(),
        "actionable_gaps": [g.model_dump() for g in actionable_gaps],
        "iterations_history": [it.model_dump() for it in updated_loop_state.iterations],
        "agent_logs": [{
            "agent": "sufficiency",
            "status": "success",
            "message": (
                f"Evaluated iteration {updated_loop_state.current_iteration}: status={sufficiency.status.value}, "
                f"action={decision.action.value}, reason={decision.stop_reason.value if decision.stop_reason else 'target_gap'}"
            )
        }]
    }


def sufficiency_router(state: ResearchState) -> str:
    """
    Routes to targeted_query if another iteration is warranted,
    otherwise routes to report generation.
    """
    decision_dict = state.get("research_decision") or {}
    action = decision_dict.get("action", "STOP_RESEARCH")

    if action == "CONTINUE_RESEARCH":
        logger.info("Sufficiency router: Continuing research loop -> routing to targeted_query")
        return "targeted_query"

    logger.info("Sufficiency router: Stopping research loop -> routing to report")
    return "report"


# -----------------------------
# TARGETED QUERY FORMULATION NODE (Stage 5)
# -----------------------------

def targeted_query_node(state: ResearchState) -> Dict[str, Any]:
    """
    Formulates a targeted search query addressing the selected research gap.
    """
    loop_state_dict = state.get("loop_state") or {}
    loop_state = ResearchLoopState(**loop_state_dict)
    decision_dict = state.get("research_decision") or {}
    decision = ResearchDecision(**decision_dict)

    original_query = loop_state.executed_queries[0] if loop_state.executed_queries else state.get("query", "")

    targeted_query = _loop_controller.plan_next_query(
        parent_query=original_query,
        decision=decision,
        loop_state=loop_state
    )

    stream_log(
        f"Targeted Query Reformulated for Iteration {loop_state.current_iteration}: "
        f"'{targeted_query.query_text}' (Strategy: {targeted_query.strategy})"
    )
    emit_lifecycle_event("targeted_query", {
        "query": targeted_query.query_text,
        "strategy": targeted_query.strategy,
        "iteration": loop_state.current_iteration
    })

    return {
        "query": targeted_query.query_text,
        "current_iteration": loop_state.current_iteration,
        "loop_state": loop_state.model_dump(),
        "active_targeted_query": targeted_query.model_dump(),
        "agent_logs": [{
            "agent": "targeted_query",
            "status": "success",
            "message": f"Generated targeted query for iter {loop_state.current_iteration}: '{targeted_query.query_text}'"
        }]
    }


# -----------------------------
# REPORT GENERATION NODE
# -----------------------------

def report_node(state: ResearchState) -> Dict[str, Any]:
    """Assembles the final comprehensive research brief and persists session state."""
    query = state.get("query", "")
    summaries = state.get("summaries", [])
    citations = state.get("citations", [])
    intelligence = state.get("intelligence", {})

    claims = state.get("claims", [])
    grounded_summary = state.get("grounded_summary", "")
    citation_verification = state.get("citation_verification")
    evidence_registry = state.get("evidence_registry", [])
    loop_state = state.get("loop_state")

    report = generate_report(
        query=query,
        summaries=summaries,
        citations=citations,
        intelligence=intelligence,
        claims=claims,
        grounded_summary=grounded_summary,
        citation_verification=citation_verification,
        evidence_registry=evidence_registry,
        loop_state=loop_state
    )

    session_data = {
        "query": query,
        "search_plan": state.get("search_plan"),
        "papers": state.get("papers", []),
        "retrieved_documents": state.get("retrieved_documents", []),
        "evidence_registry": evidence_registry,
        "claims": claims,
        "grounded_summary": grounded_summary,
        "citation_verification": citation_verification,
        "grounding_status": state.get("grounding_status", "UNGROUNDED"),
        "summaries": summaries,
        "citations": citations,
        "intelligence": intelligence,
        "cross_paper_findings": state.get("cross_paper_findings", []),
        "study_comparisons": state.get("study_comparisons", []),
        "contradiction_findings": state.get("contradiction_findings", []),
        "evidence_strength": state.get("evidence_strength"),
        "research_gaps": state.get("research_gaps", []),
        "consensus_synthesis": state.get("consensus_synthesis"),
        "current_iteration": state.get("current_iteration", 1),
        "loop_state": loop_state,
        "sufficiency_evaluation": state.get("sufficiency_evaluation"),
        "research_decision": state.get("research_decision"),
        "actionable_gaps": state.get("actionable_gaps", []),
        "iterations_history": state.get("iterations_history", []),
        "report": report,
        "execution_status": "completed"
    }

    thread_id = state.get("thread_id", query)
    save_session(thread_id, session_data)

    stream_log("Report Generated")

    return {
        "report": report,
        "execution_status": "completed",
        "agent_logs": [{
            "agent": "report",
            "status": "success",
            "message": "Final report generated and session saved"
        }]
    }


# =====================================================
# GRAPH COMPILATION
# =====================================================

builder = StateGraph(ResearchState)

# Nodes
builder.add_node("supervisor", supervisor_node)
builder.add_node("search", search_node)
builder.add_node("rag", rag_node)
builder.add_node("summary", summary_node)
builder.add_node("citation", citation_node)
builder.add_node("intelligence", intelligence_node)
builder.add_node("sufficiency", sufficiency_node)
builder.add_node("targeted_query", targeted_query_node)
builder.add_node("report", report_node)

# Entry Point
builder.add_edge(START, "supervisor")

# Routing
builder.add_conditional_edges("supervisor", supervisor_router)
builder.add_conditional_edges("search", search_router)
builder.add_edge("rag", "summary")
builder.add_conditional_edges("summary", summary_router)
builder.add_edge("citation", "intelligence")
builder.add_edge("intelligence", "sufficiency")
builder.add_conditional_edges("sufficiency", sufficiency_router)
builder.add_edge("targeted_query", "search")
builder.add_edge("report", END)

# Compiled Graph with SQLite Checkpointer
research_graph = builder.compile(
    checkpointer=checkpointer
)