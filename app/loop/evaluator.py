"""
Evidence Sufficiency Evaluator for Stage 5 Agentic Research Loop.
Provides deterministic, explainable qualitative evaluation of evidence sufficiency
and enforces loop stopping conditions without fake numerical scores.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import (
    ActionableResearchGap,
    EvidenceSufficiency,
    ResearchAction,
    ResearchDecision,
    ResearchLoopState,
    ResearchStopReason,
    SufficiencyStatus,
)


class EvidenceSufficiencyEvaluator:
    """
    Evaluates evidence completeness, unsupported claims, evidence concentration,
    and unresolved contradictions to decide whether to continue the research loop.
    """

    def __init__(self):
        self.settings = get_settings()

    def evaluate(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        evidence_registry: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
        intelligence: Dict[str, Any],
        loop_state: ResearchLoopState,
        actionable_gaps: List[ActionableResearchGap],
    ) -> Tuple[EvidenceSufficiency, ResearchDecision]:
        """
        Executes deterministic sufficiency evaluation and determines next loop action.
        """
        paper_count = len(papers)
        evidence_chunk_count = len(evidence_registry)

        # Count claim statuses
        supported_claim_count = 0
        partially_supported_count = 0
        unsupported_claim_count = 0
        unanswered_subquestions: List[str] = []

        for c in claims:
            status = str(c.get("support_status", "UNSUPPORTED")).upper()
            if status == "SUPPORTED":
                supported_claim_count += 1
            elif status == "PARTIALLY_SUPPORTED":
                partially_supported_count += 1
                unsupported_claim_count += 1
                unanswered_subquestions.append(c.get("claim_text", "")[:80])
            else:
                unsupported_claim_count += 1
                unanswered_subquestions.append(c.get("claim_text", "")[:80])

        # Evidence concentration check: Is all evidence derived from a single paper?
        unique_papers_in_evidence = {
            chunk.get("paper_id") for chunk in evidence_registry if chunk.get("paper_id")
        }
        is_concentrated = len(unique_papers_in_evidence) <= 1 and evidence_chunk_count > 0

        # Contradiction check: Are there unresolved direct result conflicts?
        contradictions = intelligence.get("contradictions", [])
        direct_conflicts = [
            c for c in contradictions
            if c.get("is_genuine_contradiction") or str(c.get("contradiction_type", "")).upper() == "DIRECT_RESULT_CONFLICT"
        ]
        has_unresolved_contradictions = len(direct_conflicts) > 0

        # Assess qualitative sufficiency tier
        status, rationale = self._determine_sufficiency_status(
            paper_count=paper_count,
            evidence_count=evidence_chunk_count,
            supported_count=supported_claim_count,
            unsupported_count=unsupported_claim_count,
            is_concentrated=is_concentrated,
            has_conflicts=has_unresolved_contradictions,
            actionable_gaps=actionable_gaps,
            evidence_strength=intelligence.get("evidence_strength")
        )

        is_additional_warranted = status in (
            SufficiencyStatus.PARTIALLY_SUFFICIENT,
            SufficiencyStatus.INSUFFICIENT,
            SufficiencyStatus.CONFLICTED
        ) and bool(actionable_gaps)

        sufficiency = EvidenceSufficiency(
            status=status,
            rationale=rationale,
            paper_count=paper_count,
            evidence_chunk_count=evidence_chunk_count,
            supported_claim_count=supported_claim_count,
            unsupported_claim_count=unsupported_claim_count,
            is_concentrated_in_single_paper=is_concentrated,
            has_unresolved_contradictions=has_unresolved_contradictions,
            unanswered_subquestions=unanswered_subquestions[:5],
            is_additional_research_warranted=is_additional_warranted
        )

        # Make stopping / continuing decision based on deterministic safety limits
        decision = self._decide_action(
            sufficiency=sufficiency,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        logger.info(
            f"[Stage 5 Sufficiency] status={sufficiency.status.value}, decision={decision.action.value}, "
            f"stop_reason={decision.stop_reason.value if decision.stop_reason else 'NONE'}, "
            f"papers={paper_count}, evidence={evidence_chunk_count}, supported_claims={supported_claim_count}"
        )

        return sufficiency, decision

    def _determine_sufficiency_status(
        self,
        paper_count: int,
        evidence_count: int,
        supported_count: int,
        unsupported_count: int,
        is_concentrated: bool,
        has_conflicts: bool,
        actionable_gaps: List[ActionableResearchGap],
        evidence_strength: Optional[Dict[str, Any]]
    ) -> Tuple[SufficiencyStatus, str]:
        """Categorizes research sufficiency into 5 explainable qualitative states."""
        # 1. No Reliable Evidence
        if paper_count == 0 or evidence_count == 0:
            return (
                SufficiencyStatus.NO_RELIABLE_EVIDENCE,
                "No relevant papers or verified evidence chunks were retrieved."
            )

        if supported_count == 0 and unsupported_count > 0 and evidence_count < 2:
            return (
                SufficiencyStatus.NO_RELIABLE_EVIDENCE,
                "Retrieved chunks failed to substantiate any generated research claims."
            )

        # 2. Conflicted
        if has_conflicts:
            strength_rating = str(evidence_strength.get("rating", "") if evidence_strength else "").upper()
            return (
                SufficiencyStatus.CONFLICTED,
                f"Retrieved literature contains direct empirical contradictions (strength={strength_rating or 'MIXED'})."
            )

        # 3. Insufficient
        if is_concentrated and paper_count > 1:
            return (
                SufficiencyStatus.INSUFFICIENT,
                "Evidence is concentrated in a single paper despite multiple candidate retrievals; broader cross-study validation needed."
            )

        if paper_count < 2 or evidence_count < 2:
            return (
                SufficiencyStatus.INSUFFICIENT,
                f"Retrieved corpus is too sparse ({paper_count} papers, {evidence_count} evidence chunks) to establish a cross-study consensus."
            )

        if supported_count == 0 and unsupported_count > 0:
            return (
                SufficiencyStatus.INSUFFICIENT,
                f"All {unsupported_count} claims remain unsupported by current evidence."
            )

        # 4. Partially Sufficient
        high_severity_gaps = [g for g in actionable_gaps if g.severity == "HIGH"]
        if high_severity_gaps or unsupported_count > 0 or paper_count < 3:
            reasons = []
            if high_severity_gaps:
                reasons.append(f"{len(high_severity_gaps)} high-severity literature gaps")
            if unsupported_count > 0:
                reasons.append(f"{unsupported_count} unverified claims")
            if paper_count < 3:
                reasons.append(f"only {paper_count} papers retrieved")
            return (
                SufficiencyStatus.PARTIALLY_SUFFICIENT,
                f"Found supporting evidence ({supported_count} supported claims), but research is incomplete due to {', '.join(reasons)}."
            )

        # 5. Sufficient
        return (
            SufficiencyStatus.SUFFICIENT,
            f"Evidence is sufficient: {paper_count} verified papers, {evidence_count} evidence chunks, "
            f"{supported_count} supported claims, zero unresolved direct contradictions, and no high-severity gaps."
        )

    def _decide_action(
        self,
        sufficiency: EvidenceSufficiency,
        loop_state: ResearchLoopState,
        actionable_gaps: List[ActionableResearchGap]
    ) -> ResearchDecision:
        """
        Determines whether to continue research or stop.
        Strictly prioritizes safety limits over LLM desires.
        """
        # Safety Check 1: Maximum Iterations Reached
        if loop_state.current_iteration >= loop_state.max_iterations:
            return ResearchDecision(
                action=ResearchAction.STOP_RESEARCH,
                stop_reason=ResearchStopReason.MAX_ITERATIONS_REACHED,
                sufficiency=sufficiency,
                rationale=f"Configured maximum iteration limit ({loop_state.max_iterations}) reached."
            )

        # Safety Check 2: Research Budget Exhausted
        if loop_state.total_search_calls >= self.settings.MAX_RESEARCH_BUDGET_CALLS:
            return ResearchDecision(
                action=ResearchAction.STOP_RESEARCH,
                stop_reason=ResearchStopReason.BUDGET_EXHAUSTED,
                sufficiency=sufficiency,
                rationale=f"Total research budget calls limit ({self.settings.MAX_RESEARCH_BUDGET_CALLS}) reached."
            )

        if len(loop_state.cumulative_paper_ids) >= self.settings.MAX_CUMULATIVE_PAPERS:
            return ResearchDecision(
                action=ResearchAction.STOP_RESEARCH,
                stop_reason=ResearchStopReason.BUDGET_EXHAUSTED,
                sufficiency=sufficiency,
                rationale=f"Cumulative paper limit ({self.settings.MAX_CUMULATIVE_PAPERS}) reached."
            )

        # Safety Check 3: Consecutive No Progress
        if loop_state.consecutive_no_progress_count >= 1 and loop_state.current_iteration > 1:
            return ResearchDecision(
                action=ResearchAction.STOP_RESEARCH,
                stop_reason=ResearchStopReason.NO_PROGRESS,
                sufficiency=sufficiency,
                rationale="Targeted search produced no new candidate papers or evidence chunks; terminating loop to avoid spinning."
            )

        # Stopping Check 4: Evidence is already Sufficient
        if sufficiency.status == SufficiencyStatus.SUFFICIENT:
            return ResearchDecision(
                action=ResearchAction.STOP_RESEARCH,
                stop_reason=ResearchStopReason.EVIDENCE_SUFFICIENT,
                sufficiency=sufficiency,
                rationale="Current evidence base is sufficient to address the research query without additional search."
            )

        # Stopping Check 5: Provider Exhaustion on initial empty search
        if sufficiency.status == SufficiencyStatus.NO_RELIABLE_EVIDENCE and loop_state.current_iteration == 1 and sufficiency.paper_count == 0:
            return ResearchDecision(
                action=ResearchAction.STOP_RESEARCH,
                stop_reason=ResearchStopReason.PROVIDER_EXHAUSTION,
                sufficiency=sufficiency,
                rationale="Initial academic search providers returned 0 candidates. Cannot continue without baseline evidence."
            )

        # Evaluation Check 6: Can we continue with an actionable gap?
        unaddressed_gaps = [
            g for g in actionable_gaps
            if g.gap_id not in loop_state.executed_gap_ids
        ]

        if not unaddressed_gaps:
            return ResearchDecision(
                action=ResearchAction.STOP_RESEARCH,
                stop_reason=ResearchStopReason.NO_ACTIONABLE_GAPS,
                sufficiency=sufficiency,
                rationale="No unaddressed actionable research gaps remain in the retrieved literature."
            )

        # Select highest-severity actionable gap
        selected_gap = sorted(
            unaddressed_gaps,
            key=lambda g: (0 if g.severity == "HIGH" else (1 if g.severity == "MEDIUM" else 2))
        )[0]

        return ResearchDecision(
            action=ResearchAction.CONTINUE_RESEARCH,
            stop_reason=None,
            sufficiency=sufficiency,
            selected_gap=selected_gap,
            rationale=f"Evidence is {sufficiency.status.value}; targeting {selected_gap.severity} gap '{selected_gap.gap_id}': {selected_gap.description[:100]}"
        )
