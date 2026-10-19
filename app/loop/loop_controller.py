"""
Research Loop Controller for Stage 5 Agentic Research Loop.
Orchestrates iteration lifecycle, provenance accretion, progress tracking,
and structured observability.
"""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import (
    ActionableResearchGap,
    EvidenceSufficiency,
    ResearchDecision,
    ResearchIteration,
    ResearchLoopState,
    ResearchStopReason,
    TargetedResearchQuery,
)
from app.loop.evaluator import EvidenceSufficiencyEvaluator
from app.loop.gap_analyzer import ActionableGapAnalyzer
from app.loop.query_planner import TargetedQueryPlanner


class ResearchLoopController:
    """
    State manager and coordinator for the agentic research loop.
    Enforces loop limits, deduplication, and provenance across iterations.
    """

    def __init__(self):
        self.settings = get_settings()
        self.evaluator = EvidenceSufficiencyEvaluator()
        self.gap_analyzer = ActionableGapAnalyzer()
        self.query_planner = TargetedQueryPlanner()

    def initialize_state(
        self,
        initial_query: str,
        max_iterations: Optional[int] = None
    ) -> ResearchLoopState:
        """Initializes fresh loop state for a research run."""
        max_iter = max_iterations or self.settings.MAX_RESEARCH_LOOP_ITERATIONS
        return ResearchLoopState(
            current_iteration=1,
            max_iterations=max_iter,
            executed_queries=[initial_query],
            total_search_calls=1
        )

    def decide_next_step(
        self,
        loop_state: ResearchLoopState,
        current_iteration: int = 1,
        papers: Optional[List[Dict[str, Any]]] = None,
        evidence_registry: Optional[List[Dict[str, Any]]] = None,
        claims: Optional[List[Dict[str, Any]]] = None,
        intelligence: Optional[Dict[str, Any]] = None,
        actionable_gaps: Optional[List[ActionableResearchGap]] = None,
        query: Optional[str] = None,
        **kwargs: Any
    ) -> ResearchDecision:
        """Evaluates evidence sufficiency and returns ResearchDecision."""
        loop_state.current_iteration = current_iteration
        sufficiency, decision = self.evaluator.evaluate(
            query=query or (loop_state.executed_queries[0] if loop_state.executed_queries else ""),
            papers=papers or [],
            evidence_registry=evidence_registry or [],
            claims=claims or [],
            intelligence=intelligence or {},
            loop_state=loop_state,
            actionable_gaps=actionable_gaps or []
        )
        return decision

    def evaluate_and_record_iteration(
        self,
        query: str,
        search_plan: Optional[Dict[str, Any]],
        papers: List[Dict[str, Any]],
        evidence_registry: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
        intelligence: Dict[str, Any],
        loop_state: ResearchLoopState,
        session_id: str,
        start_time: float,
    ) -> Tuple[EvidenceSufficiency, ResearchDecision, List[ActionableResearchGap], ResearchLoopState]:
        """
        Executes end-of-iteration audit:
        1. Identifies actionable gaps.
        2. Evaluates sufficiency and stopping limits.
        3. Updates progress and cumulative IDs.
        4. Records ResearchIteration entry.
        5. Emits structured observability log.
        """
        # 1. Identify actionable gaps
        actionable_gaps = self.gap_analyzer.analyze(
            query=query,
            papers=papers,
            evidence_registry=evidence_registry,
            claims=claims,
            intelligence=intelligence,
        )

        # 2. Check newly acquired papers and evidence
        current_paper_ids = [str(p.get("paper_id") or p.get("id")) for p in papers if (p.get("paper_id") or p.get("id"))]
        current_evidence_ids = [str(e.get("evidence_id")) for e in evidence_registry if e.get("evidence_id")]

        new_paper_ids = [pid for pid in current_paper_ids if pid not in loop_state.cumulative_paper_ids]
        new_evidence_ids = [eid for eid in current_evidence_ids if eid not in loop_state.cumulative_evidence_ids]

        new_paper_count = len(new_paper_ids)
        new_evidence_count = len(new_evidence_ids)

        # Check progress: if this is iteration > 1 and nothing new was retrieved
        if loop_state.current_iteration > 1:
            if new_paper_count == 0 and new_evidence_count == 0:
                loop_state.consecutive_no_progress_count += 1
                logger.warning(
                    f"[Stage 5 LoopController] Iteration {loop_state.current_iteration} produced 0 new papers "
                    f"and 0 new evidence chunks (no-progress count: {loop_state.consecutive_no_progress_count})"
                )
            else:
                loop_state.consecutive_no_progress_count = 0

        # Update cumulative tracking
        for pid in new_paper_ids:
            if pid not in loop_state.cumulative_paper_ids:
                loop_state.cumulative_paper_ids.append(pid)

        for eid in new_evidence_ids:
            if eid not in loop_state.cumulative_evidence_ids:
                loop_state.cumulative_evidence_ids.append(eid)

        # 3. Evaluate sufficiency and decide next step
        sufficiency, decision = self.evaluator.evaluate(
            query=query,
            papers=papers,
            evidence_registry=evidence_registry,
            claims=claims,
            intelligence=intelligence,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        # Count claim statuses
        supported_cnt = sum(1 for c in claims if str(c.get("support_status", "")).upper() == "SUPPORTED")
        partially_cnt = sum(1 for c in claims if str(c.get("support_status", "")).upper() == "PARTIALLY_SUPPORTED")
        unsupported_cnt = sum(1 for c in claims if str(c.get("support_status", "")).upper() in ("UNSUPPORTED", "INSUFFICIENT_EVIDENCE"))

        # 4. Construct ResearchIteration audit object
        iteration_record = ResearchIteration(
            iteration_id=loop_state.current_iteration,
            parent_iteration_id=loop_state.current_iteration - 1 if loop_state.current_iteration > 1 else None,
            query_used=query,
            search_plan=search_plan,
            retrieved_paper_ids=current_paper_ids,
            new_paper_count=new_paper_count if loop_state.current_iteration > 1 else len(current_paper_ids),
            cumulative_paper_count=len(loop_state.cumulative_paper_ids),
            retrieved_evidence_ids=current_evidence_ids,
            new_evidence_count=new_evidence_count if loop_state.current_iteration > 1 else len(current_evidence_ids),
            cumulative_evidence_count=len(loop_state.cumulative_evidence_ids),
            supported_claims_count=supported_cnt,
            partially_supported_claims_count=partially_cnt,
            unsupported_claims_count=unsupported_cnt,
            research_findings_count=len(intelligence.get("findings", [])),
            detected_gaps=[g.gap_id for g in actionable_gaps],
            decision=decision,
            stop_reason=decision.stop_reason,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        loop_state.iterations.append(iteration_record)
        if decision.stop_reason:
            loop_state.final_stop_reason = decision.stop_reason

        # 5. Record executed gap if continuing
        if decision.selected_gap and decision.selected_gap.gap_id not in loop_state.executed_gap_ids:
            loop_state.executed_gap_ids.append(decision.selected_gap.gap_id)

        # 6. Observability structured logging (Section 12)
        elapsed_seconds = round(time.time() - start_time, 2)
        logger.info(
            f"[Agentic Research Loop Event] session_id={session_id} iteration={loop_state.current_iteration} "
            f"query='{query[:50]}' papers={len(papers)} (new={new_paper_count}) "
            f"evidence={len(evidence_registry)} (new={new_evidence_count}) "
            f"claims=[sup={supported_cnt}, part={partially_cnt}, unsup={unsupported_cnt}] "
            f"gaps={len(actionable_gaps)} action={decision.action.value} "
            f"stop_reason={decision.stop_reason.value if decision.stop_reason else 'NONE'} "
            f"duration={elapsed_seconds}s"
        )

        return sufficiency, decision, actionable_gaps, loop_state

    def plan_next_query(
        self,
        parent_query: str,
        decision: ResearchDecision,
        loop_state: ResearchLoopState
    ) -> TargetedResearchQuery:
        """
        Formulates the targeted query for the next iteration based on the selected gap.
        """
        if not decision.selected_gap:
            raise ValueError("Cannot plan next query without a selected actionable gap")

        next_iter = loop_state.current_iteration + 1
        targeted_query = self.query_planner.plan_targeted_query(
            parent_query=parent_query,
            gap=decision.selected_gap,
            executed_queries=loop_state.executed_queries,
            iteration=next_iter
        )

        loop_state.executed_queries.append(targeted_query.query_text)
        loop_state.active_targeted_query = targeted_query
        loop_state.current_iteration = next_iter
        loop_state.total_search_calls += 1

        return targeted_query
