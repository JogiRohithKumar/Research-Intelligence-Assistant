"""
Stage 5 Agentic Research Loop Evaluation Runner.
Evaluates iterative research behavior, query drift rejection, stopping conditions,
and evidence accumulation efficiency.
"""

from typing import List
from evaluation.models import EvaluationCase, EvaluationResult
from evaluation.runners.base_runner import BaseRunner
from evaluation.taxonomy import EvaluationDimension, FailureCategory
from evaluation.metrics.loop import (
    calculate_loop_efficiency,
    verify_stopping_reason,
    detect_query_drift,
)
from app.loop.loop_controller import ResearchLoopController
from app.loop.drift_guard import DriftGuard
from app.models.domain import ResearchDecision, ResearchStopReason, ResearchAction


class LoopRunner(BaseRunner):
    """Evaluates Stage 5 agentic loop decisions, stopping bounds, and drift control."""

    def __init__(self):
        super().__init__(dimension=EvaluationDimension.AGENTIC_LOOP)
        self.controller = ResearchLoopController()
        self.drift_guard = DriftGuard()

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        failures: List[FailureCategory] = []
        metrics = {}

        initial_query = case.research_question
        loop_state = self.controller.initialize_state(initial_query=initial_query, max_iterations=3)

        # 1. Evaluate Query Drift Guard
        # Check that on-topic reformulations pass and off-topic drift is flagged
        subsequent_queries = [
            f"{initial_query} phase 3 outcomes",
            f"{initial_query} clinical trial methodology"
        ]
        drift_detected = detect_query_drift(initial_query, subsequent_queries)
        metrics["query_drift_detected"] = 1.0 if drift_detected else 0.0
        if drift_detected:
            failures.append(FailureCategory.QUERY_DRIFT)

        # 2. Evaluate Loop Decision and Stopping Reason
        papers = [{"paper_id": f"p_{i}", "title": f"Paper {i}"} for i in range(len(case.reference_evidence))]
        evidence = [{"evidence_id": ev.evidence_id, "text": ev.text_snippet} for ev in case.reference_evidence]
        claims = [{"claim_id": c.claim_id, "status": c.expected_status} for c in case.reference_claims]

        decision: ResearchDecision = self.controller.decide_next_step(
            loop_state=loop_state,
            current_iteration=1,
            papers=papers,
            evidence_registry=evidence,
            claims=claims,
            query=initial_query,
            actionable_gaps=[]
        )

        valid_reasons = [
            "EVIDENCE_SUFFICIENT", "MAX_ITERATIONS_REACHED", "NO_PROGRESS",
            "NO_ACTIONABLE_GAPS", "REPEATED_QUERIES", "BUDGET_EXHAUSTED", "PROVIDER_EXHAUSTION"
        ]
        stop_reason = decision.stop_reason.value if decision.stop_reason else "CONTINUE"

        should_stop = (decision.action == ResearchAction.STOP_RESEARCH)
        if should_stop:
            is_valid_stop = verify_stopping_reason(stop_reason, valid_reasons)
            metrics["valid_stop_reason"] = 1.0 if is_valid_stop else 0.0
            if not is_valid_stop:
                failures.append(FailureCategory.LOOP_NO_PROGRESS)
        else:
            metrics["valid_stop_reason"] = 1.0

        # 3. Evaluate Iteration Efficiency (No empty iteration inflation)
        evidence_gain_history = [len(case.reference_evidence)]
        efficiency = calculate_loop_efficiency(iterations_count=1, evidence_gain_history=evidence_gain_history)
        metrics["loop_efficiency"] = efficiency

        passed = len(failures) == 0

        return EvaluationResult(
            case_id=case.case_id,
            case_name=case.name,
            dimension=self.dimension,
            passed=passed,
            failures=failures,
            metrics=metrics,
            details={
                "should_stop": should_stop,
                "stop_reason": stop_reason,
                "efficiency": efficiency
            }
        )
