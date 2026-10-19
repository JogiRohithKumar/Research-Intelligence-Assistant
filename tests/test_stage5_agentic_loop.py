"""
Comprehensive Stage 5 Agentic Research Loop Test Suite.
Verifies evidence sufficiency evaluation, grounded gap identification, targeted query planning,
drift protection, safety budgets, no-progress termination, multi-iteration provenance,
and end-to-end LangGraph loop orchestration.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from app.core.config import get_settings
from app.loop.drift_guard import QueryDriftGuard
from app.loop.evaluator import EvidenceSufficiencyEvaluator
from app.loop.gap_analyzer import ActionableGapAnalyzer
from app.loop.loop_controller import ResearchLoopController
from app.loop.query_planner import TargetedQueryPlanner
from app.models.domain import (
    ActionableResearchGap,
    ClaimSupportStatus,
    EvidenceChunk,
    EvidenceSourceType,
    EvidenceStrength,
    EvidenceStrengthRating,
    EvidenceSufficiency,
    ResearchAction,
    ResearchClaim,
    ResearchDecision,
    ResearchIteration,
    ResearchLoopState,
    ResearchStopReason,
    SufficiencyStatus,
    TargetedResearchQuery,
)
from app.rag.evidence import EvidenceRegistry
from app.rag.evidence_retriever import EvidenceRetriever
from app.graph.research_graph import research_graph


class TestStage5AgenticResearchLoop(unittest.TestCase):
    def setUp(self):
        self.settings = get_settings()
        self.evaluator = EvidenceSufficiencyEvaluator()
        self.gap_analyzer = ActionableGapAnalyzer()
        self.drift_guard = QueryDriftGuard()
        self.query_planner = TargetedQueryPlanner()
        self.loop_controller = ResearchLoopController()

    # =========================================================================
    # 1. SUFFICIENCY & DECISION TESTS
    # =========================================================================

    def test_sufficient_evidence_stops_loop(self):
        """When evidence is multi-study, consistent, and has 0 unsupported claims, loop stops."""
        papers = [{"paper_id": "P1"}, {"paper_id": "P2"}, {"paper_id": "P3"}]
        evidence = [
            {"evidence_id": "E001", "paper_id": "P1"},
            {"evidence_id": "E002", "paper_id": "P2"},
            {"evidence_id": "E003", "paper_id": "P3"},
            {"evidence_id": "E004", "paper_id": "P1"},
        ]
        claims = [
            {"claim_id": "C1", "claim_text": "Claim 1", "support_status": "SUPPORTED"},
            {"claim_id": "C2", "claim_text": "Claim 2", "support_status": "SUPPORTED"},
        ]
        intelligence = {
            "findings": [{"finding_id": "F1", "finding_type": "AGREEMENT"}],
            "contradictions": [],
            "gaps": [],
            "evidence_strength": {"rating": "STRONG"}
        }
        loop_state = self.loop_controller.initialize_state("quantum coherence fluxonium", max_iterations=3)
        actionable_gaps = []

        sufficiency, decision = self.evaluator.evaluate(
            query="quantum coherence fluxonium",
            papers=papers,
            evidence_registry=evidence,
            claims=claims,
            intelligence=intelligence,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        self.assertEqual(sufficiency.status, SufficiencyStatus.SUFFICIENT)
        self.assertEqual(decision.action, ResearchAction.STOP_RESEARCH)
        self.assertEqual(decision.stop_reason, ResearchStopReason.EVIDENCE_SUFFICIENT)
        self.assertFalse(sufficiency.is_additional_research_warranted)

    def test_insufficient_evidence_triggers_targeted_search(self):
        """When evidence is sparse or concentrated in 1 paper, evaluator continues research."""
        papers = [{"paper_id": "P1"}]
        evidence = [{"evidence_id": "E001", "paper_id": "P1"}]
        claims = [{"claim_id": "C1", "claim_text": "Claim 1", "support_status": "SUPPORTED"}]
        intelligence = {"contradictions": [], "gaps": []}
        loop_state = self.loop_controller.initialize_state("sparse research topic", max_iterations=3)

        actionable_gaps = [
            ActionableResearchGap(
                gap_id="GAP_CONCENTRATION_01",
                title="Single Study Concentration",
                description="Within the retrieved literature, all verified evidence originates from a single study.",
                category="GENERALIZATION_GAP",
                severity="HIGH",
                recommended_research_action="Search for independent replication"
            )
        ]

        sufficiency, decision = self.evaluator.evaluate(
            query="sparse research topic",
            papers=papers,
            evidence_registry=evidence,
            claims=claims,
            intelligence=intelligence,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        self.assertEqual(sufficiency.status, SufficiencyStatus.INSUFFICIENT)
        self.assertEqual(decision.action, ResearchAction.CONTINUE_RESEARCH)
        self.assertIsNone(decision.stop_reason)
        self.assertIsNotNone(decision.selected_gap)
        self.assertEqual(decision.selected_gap.gap_id, "GAP_CONCENTRATION_01")

    def test_contradictory_evidence_triggers_conflicted_state(self):
        """Genuine direct result contradictions produce CONFLICTED status."""
        papers = [{"paper_id": "P1"}, {"paper_id": "P2"}]
        evidence = [{"evidence_id": "E001", "paper_id": "P1"}, {"evidence_id": "E002", "paper_id": "P2"}]
        claims = [
            {"claim_id": "C1", "support_status": "SUPPORTED"},
            {"claim_id": "C2", "support_status": "SUPPORTED"}
        ]
        intelligence = {
            "contradictions": [{
                "contradiction_id": "CT01",
                "topic": "coherence time",
                "is_genuine_contradiction": True,
                "contradiction_type": "DIRECT_RESULT_CONFLICT",
                "claim_a": "increases coherence",
                "claim_b": "decreases coherence",
                "paper_a_id": "P1",
                "paper_b_id": "P2"
            }],
            "evidence_strength": {"rating": "MIXED"}
        }
        loop_state = self.loop_controller.initialize_state("qubit coherence comparison", max_iterations=3)
        actionable_gaps = self.gap_analyzer.analyze(
            query="qubit coherence comparison",
            papers=papers,
            evidence_registry=evidence,
            claims=claims,
            intelligence=intelligence
        )

        sufficiency, decision = self.evaluator.evaluate(
            query="qubit coherence comparison",
            papers=papers,
            evidence_registry=evidence,
            claims=claims,
            intelligence=intelligence,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        self.assertEqual(sufficiency.status, SufficiencyStatus.CONFLICTED)
        self.assertTrue(sufficiency.has_unresolved_contradictions)
        self.assertEqual(decision.action, ResearchAction.CONTINUE_RESEARCH)
        self.assertEqual(decision.selected_gap.category, "CONTRADICTION")

    # =========================================================================
    # 2. GAP IDENTIFICATION & TARGETED QUERY TESTS
    # =========================================================================

    def test_targeted_query_addresses_correct_gap(self):
        """Planner formulates a query targeted specifically to the gap category."""
        parent_query = "retrieval augmented generation factual accuracy"
        gap = ActionableResearchGap(
            gap_id="GAP_POP_01",
            title="Medical Cohort Missing",
            description="Within the retrieved literature, evaluations are restricted to general QA; medical datasets are absent.",
            category="POPULATION_GAP",
            severity="HIGH",
            recommended_research_action="Search for medical cohort benchmark studies."
        )

        targeted_query = self.query_planner.plan_targeted_query(
            parent_query=parent_query,
            gap=gap,
            executed_queries=[parent_query],
            iteration=2
        )

        self.assertEqual(targeted_query.parent_query, parent_query)
        self.assertEqual(targeted_query.gap_addressed_id, "GAP_POP_01")
        self.assertEqual(targeted_query.strategy, "POPULATION_FOCUSED")
        self.assertEqual(targeted_query.iteration, 2)
        # Verify parent anchor terms preserved
        self.assertIn("retrieval", targeted_query.query_text.lower())
        self.assertIn("accuracy", targeted_query.query_text.lower())

    def test_query_drift_is_rejected_and_anchored(self):
        """QueryDriftGuard detects completely drifted queries and enforces topical anchoring."""
        parent_query = "quantum error correction surface codes"
        drifted_query = "convolutional neural network image segmentation"

        is_drift, overlap, msg = self.drift_guard.check_drift(parent_query, drifted_query)
        self.assertTrue(is_drift)
        self.assertEqual(overlap, 0.0)

        # Enforce anchoring
        anchored = self.drift_guard.enforce_anchor(
            parent_query=parent_query,
            proposed_query=drifted_query,
            target_concepts=["fault", "tolerance"]
        )
        self.assertIn("quantum", anchored.lower())
        self.assertIn("error", anchored.lower())
        self.assertIn("tolerance", anchored.lower())

    def test_repeated_query_is_detected_and_modified(self):
        """TargetedQueryPlanner avoids executing identical search strings repeatedly."""
        parent_query = "superconducting fluxonium coherence"
        gap = ActionableResearchGap(
            gap_id="GAP_01",
            title="Generalization Gap",
            description="Replication studies missing",
            category="GENERALIZATION_GAP",
            severity="MEDIUM"
        )
        # Mock already executed exact query
        executed = [parent_query, "superconducting fluxonium coherence empirical study"]

        targeted = self.query_planner.plan_targeted_query(
            parent_query=parent_query,
            gap=gap,
            executed_queries=executed,
            iteration=3
        )
        self.assertNotIn(targeted.query_text, executed)

    def test_repeated_gap_is_detected(self):
        """A gap that has already been executed in an earlier iteration is not selected again."""
        loop_state = self.loop_controller.initialize_state("query", max_iterations=3)
        loop_state.executed_gap_ids.append("GAP_01")

        actionable_gaps = [
            ActionableResearchGap(gap_id="GAP_01", description="Gap 1", severity="HIGH"),
            ActionableResearchGap(gap_id="GAP_02", description="Gap 2", severity="MEDIUM")
        ]

        sufficiency = EvidenceSufficiency(
            status=SufficiencyStatus.PARTIALLY_SUFFICIENT,
            rationale="Partially sufficient",
            paper_count=2,
            evidence_chunk_count=3
        )

        decision = self.evaluator._decide_action(
            sufficiency=sufficiency,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        self.assertEqual(decision.action, ResearchAction.CONTINUE_RESEARCH)
        self.assertEqual(decision.selected_gap.gap_id, "GAP_02")

    # =========================================================================
    # 3. SAFETY LIMITS & BUDGET TESTS
    # =========================================================================

    def test_maximum_iteration_limit_works(self):
        """Loop terminates when current_iteration equals max_iterations."""
        loop_state = self.loop_controller.initialize_state("test query", max_iterations=2)
        loop_state.current_iteration = 2  # At ceiling

        actionable_gaps = [ActionableResearchGap(gap_id="GAP_01", description="Gap 1")]
        sufficiency = EvidenceSufficiency(status=SufficiencyStatus.INSUFFICIENT, rationale="Still insufficient")

        decision = self.evaluator._decide_action(
            sufficiency=sufficiency,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        self.assertEqual(decision.action, ResearchAction.STOP_RESEARCH)
        self.assertEqual(decision.stop_reason, ResearchStopReason.MAX_ITERATIONS_REACHED)

    def test_research_budget_limit_works(self):
        """Loop terminates when search call budget or paper budget is exhausted."""
        loop_state = self.loop_controller.initialize_state("test query", max_iterations=5)
        loop_state.total_search_calls = self.settings.MAX_RESEARCH_BUDGET_CALLS

        actionable_gaps = [ActionableResearchGap(gap_id="GAP_01", description="Gap 1")]
        sufficiency = EvidenceSufficiency(status=SufficiencyStatus.PARTIALLY_SUFFICIENT, rationale="Incomplete")

        decision = self.evaluator._decide_action(
            sufficiency=sufficiency,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        self.assertEqual(decision.action, ResearchAction.STOP_RESEARCH)
        self.assertEqual(decision.stop_reason, ResearchStopReason.BUDGET_EXHAUSTED)

    def test_no_progress_condition_stops_loop(self):
        """If follow-up search produced 0 new papers and 0 new evidence, loop stops."""
        loop_state = self.loop_controller.initialize_state("test query", max_iterations=5)
        loop_state.current_iteration = 2
        loop_state.consecutive_no_progress_count = 1  # Triggered in previous step

        actionable_gaps = [ActionableResearchGap(gap_id="GAP_01", description="Gap 1")]
        sufficiency = EvidenceSufficiency(status=SufficiencyStatus.INSUFFICIENT, rationale="Still insufficient")

        decision = self.evaluator._decide_action(
            sufficiency=sufficiency,
            loop_state=loop_state,
            actionable_gaps=actionable_gaps
        )

        self.assertEqual(decision.action, ResearchAction.STOP_RESEARCH)
        self.assertEqual(decision.stop_reason, ResearchStopReason.NO_PROGRESS)

    def test_duplicate_papers_do_not_inflate_progress(self):
        """When follow-up search retrieves existing papers, new_paper_count is 0."""
        loop_state = self.loop_controller.initialize_state("test query", max_iterations=3)
        loop_state.cumulative_paper_ids = ["P1", "P2"]
        loop_state.cumulative_evidence_ids = ["E001"]
        loop_state.current_iteration = 2

        papers = [{"paper_id": "P1"}, {"paper_id": "P2"}]  # Duplicate papers
        evidence = [{"evidence_id": "E001", "paper_id": "P1"}]
        claims = [{"claim_id": "C1", "support_status": "SUPPORTED"}]
        intelligence = {"contradictions": [], "gaps": []}

        sufficiency, decision, gaps, updated_state = self.loop_controller.evaluate_and_record_iteration(
            query="test query",
            search_plan=None,
            papers=papers,
            evidence_registry=evidence,
            claims=claims,
            intelligence=intelligence,
            loop_state=loop_state,
            session_id="test_session",
            start_time=time.time()
        )

        last_iteration = updated_state.iterations[-1]
        self.assertEqual(last_iteration.new_paper_count, 0)
        self.assertEqual(updated_state.consecutive_no_progress_count, 1)

    # =========================================================================
    # 4. PROVENANCE & GROUNDING GATE INVARIANT TESTS
    # =========================================================================

    def test_new_evidence_is_incorporated_with_sequential_ids(self):
        """Iteration 2 appends new chunks with continuous sequential numbering without collision."""
        registry = EvidenceRegistry(run_id="test_run")
        chunk1 = EvidenceChunk(
            evidence_id="E001",
            paper_id="P1",
            chunk_id="P1_c0",
            title="Paper 1 Title",
            text="Initial evidence from paper 1",
            retrieval_score=0.9
        )
        registry.register(chunk1)
        self.assertEqual(registry.count(), 1)

        # In iteration 2, new paper P2 is added
        retriever = EvidenceRetriever()
        mock_raw_docs = [
            MagicMock(
                doc_id="P2_c0",
                paper_id="P2",
                chunk_index=0,
                content="Newly retrieved follow-up evidence from paper 2",
                paper_title="Paper 2 Title",
                score=0.95,
                metadata={"source": "arxiv"}
            )
        ]

        with patch("app.rag.evidence_retriever.retrieve_context", return_value=mock_raw_docs):
            updated_registry = retriever.retrieve_evidence(
                query="follow up targeted query",
                papers=[{"paper_id": "P1"}, {"paper_id": "P2"}],
                existing_registry=registry
            )

        self.assertEqual(updated_registry.count(), 2)
        chunk2 = updated_registry.get("E002")
        self.assertIsNotNone(chunk2)
        self.assertEqual(chunk2.paper_id, "P2")
        # Verify E001 was untouched
        self.assertEqual(updated_registry.get("E001").paper_id, "P1")

    def test_provenance_survives_multiple_iterations(self):
        """ResearchIteration records preserve query used, counts, decision, and parent links."""
        loop_state = self.loop_controller.initialize_state("initial query", max_iterations=3)
        self.assertEqual(loop_state.current_iteration, 1)

        # Iteration 1
        self.loop_controller.evaluate_and_record_iteration(
            query="initial query",
            search_plan=None,
            papers=[{"paper_id": "P1"}],
            evidence_registry=[{"evidence_id": "E001", "paper_id": "P1"}],
            claims=[{"claim_id": "C1", "support_status": "SUPPORTED"}],
            intelligence={"contradictions": [], "gaps": []},
            loop_state=loop_state,
            session_id="session_01",
            start_time=time.time()
        )

        self.assertEqual(len(loop_state.iterations), 1)
        it1 = loop_state.iterations[0]
        self.assertEqual(it1.iteration_id, 1)
        self.assertIsNone(it1.parent_iteration_id)
        self.assertEqual(it1.query_used, "initial query")

        # Plan query for iteration 2
        decision = ResearchDecision(
            action=ResearchAction.CONTINUE_RESEARCH,
            sufficiency=EvidenceSufficiency(status=SufficiencyStatus.INSUFFICIENT, rationale="Sparse"),
            selected_gap=ActionableResearchGap(gap_id="G1", description="Missing baseline")
        )
        targeted = self.loop_controller.plan_next_query("initial query", decision, loop_state)
        self.assertEqual(loop_state.current_iteration, 2)

        # Iteration 2 record
        self.loop_controller.evaluate_and_record_iteration(
            query=targeted.query_text,
            search_plan=None,
            papers=[{"paper_id": "P1"}, {"paper_id": "P2"}],
            evidence_registry=[{"evidence_id": "E001", "paper_id": "P1"}, {"evidence_id": "E002", "paper_id": "P2"}],
            claims=[{"claim_id": "C1", "support_status": "SUPPORTED"}],
            intelligence={"contradictions": [], "gaps": []},
            loop_state=loop_state,
            session_id="session_01",
            start_time=time.time()
        )

        self.assertEqual(len(loop_state.iterations), 2)
        it2 = loop_state.iterations[1]
        self.assertEqual(it2.iteration_id, 2)
        self.assertEqual(it2.parent_iteration_id, 1)
        self.assertEqual(it2.new_paper_count, 1)

    def test_provider_failure_does_not_loop_forever(self):
        """Initial empty search routes to PROVIDER_EXHAUSTION stopping reason immediately."""
        loop_state = self.loop_controller.initialize_state("non_existent_topic_xyz123", max_iterations=3)
        sufficiency, decision = self.evaluator.evaluate(
            query="non_existent_topic_xyz123",
            papers=[],
            evidence_registry=[],
            claims=[],
            intelligence={},
            loop_state=loop_state,
            actionable_gaps=[]
        )
        self.assertEqual(sufficiency.status, SufficiencyStatus.NO_RELIABLE_EVIDENCE)
        self.assertEqual(decision.action, ResearchAction.STOP_RESEARCH)
        self.assertEqual(decision.stop_reason, ResearchStopReason.PROVIDER_EXHAUSTION)

    def test_llm_structured_output_failure_handled_gracefully(self):
        """TargetedQueryPlanner falls back to deterministic query when LLM fails or hits quota."""
        with patch.object(self.query_planner, "_generate_with_llm", return_value=None):
            gap = ActionableResearchGap(
                gap_id="GAP_FAIL_01",
                description="Within the retrieved literature, evaluations lack long-term retention metrics.",
                category="OUTCOME_GAP"
            )
            targeted = self.query_planner.plan_targeted_query(
                parent_query="spaced repetition memory retention",
                gap=gap,
                executed_queries=["spaced repetition memory retention"],
                iteration=2
            )
            self.assertIsNotNone(targeted)
            self.assertEqual(targeted.strategy, "OUTCOME_FOCUSED")
            self.assertIn("spaced", targeted.query_text.lower())

    # =========================================================================
    # 5. INTEGRATION & PIPELINE TESTS
    # =========================================================================

    def test_stage5_langgraph_pipeline_execution(self):
        """End-to-end integration test verifying LangGraph executes through Stage 5 loop node."""
        initial_state = {
            "query": "superconducting qubit coherence fluxonium",
            "thread_id": f"test_stage5_{int(time.time())}",
            "retry_count": 0,
            "execution_status": "in_progress",
            "supervisor": None,
            "search_plan": None,
            "papers": [],
            "retrieved_documents": [],
            "evidence_registry": [],
            "claims": [],
            "grounded_summary": "",
            "citation_verification": None,
            "grounding_status": "UNGROUNDED",
            "summaries": [],
            "citations": [],
            "verification": None,
            "gaps": None,
            "intelligence": None,
            "cross_paper_findings": [],
            "study_comparisons": [],
            "contradiction_findings": [],
            "evidence_strength": None,
            "research_gaps": [],
            "consensus_synthesis": None,
            "current_iteration": 1,
            "max_iterations": 2,
            "loop_state": None,
            "active_targeted_query": None,
            "sufficiency_evaluation": None,
            "actionable_gaps": [],
            "research_decision": None,
            "iterations_history": [],
            "report": "",
            "final_report": None,
            "agent_logs": [],
            "errors": []
        }

        config = {"configurable": {"thread_id": initial_state["thread_id"]}}
        final_state = research_graph.invoke(initial_state, config=config)

        self.assertIn(final_state["execution_status"], ["completed", "in_progress"])
        self.assertIsNotNone(final_state.get("report"))
        self.assertGreater(len(final_state.get("report")), 100)
        self.assertIsNotNone(final_state.get("sufficiency_evaluation"))
        self.assertIsNotNone(final_state.get("loop_state"))
        self.assertGreaterEqual(len(final_state.get("loop_state", {}).get("iterations", [])), 1)


if __name__ == "__main__":
    unittest.main()
