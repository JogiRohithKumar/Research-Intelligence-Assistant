"""
Pytest Test Suite for Stage 8 Evaluation Framework.
Enables execution via `pytest evaluation/ -v`.
Validates Golden Dataset, dimensional runners, 20 adversarial red-team benchmarks,
security regression, and quality gates.
"""

import unittest
from evaluation.datasets.golden_dataset import GOLDEN_DATASET_V1
from evaluation.quality_gates import QUALITY_GATES, evaluate_quality_gates
from evaluation.runners import (
    AdversarialRunner,
    ClaimsRunner,
    IntelligenceRunner,
    LoopRunner,
    RagRunner,
    RetrievalRunner,
    SecurityRunner,
)
from evaluation.run_evaluation import execute_evaluation_run
from evaluation.taxonomy import EvaluationDimension, EvaluationVerdict, FailureCategory


class TestStage8EvaluationSuite(unittest.TestCase):
    """Automated test harness for Stage 8 evaluation."""

    def test_golden_dataset_integrity(self):
        """Verify Golden Dataset contains all 14 cases A-N with valid schemas."""
        self.assertEqual(len(GOLDEN_DATASET_V1.cases), 14)
        case_ids = {c.case_id for c in GOLDEN_DATASET_V1.cases}
        expected_ids = {
            "CASE_A_STRAIGHTFORWARD", "CASE_B_COMPARISON", "CASE_C_CONTRADICTORY",
            "CASE_D_METHODOLOGY", "CASE_E_RESEARCH_GAP", "CASE_F_SPARSE_LIT",
            "CASE_G_ITERATIVE_SEARCH", "CASE_H_INSUFFICIENT_INITIAL", "CASE_I_MISLEADING_CANDIDATE",
            "CASE_J_CAUSAL_OVERREACH", "CASE_K_QUANTITATIVE_EXTRACTION", "CASE_L_HETEROGENEOUS_PICO",
            "CASE_M_GENUINE_DISAGREEMENT", "CASE_N_INSUFFICIENT_EVIDENCE"
        }
        self.assertEqual(case_ids, expected_ids)

        for case in GOLDEN_DATASET_V1.cases:
            self.assertTrue(len(case.research_question) > 5)
            self.assertTrue(len(case.expected_behavior) > 10)
            self.assertTrue(len(case.reference_evidence) >= 1)

    def test_rag_runner_execution(self):
        """Verify Stage 3 RAG runner evaluates provenance and sufficiency."""
        runner = RagRunner()
        case_a = next(c for c in GOLDEN_DATASET_V1.cases if c.case_id == "CASE_A_STRAIGHTFORWARD")
        res = runner.evaluate_case(case_a)
        self.assertTrue(res.passed)
        self.assertEqual(res.dimension, EvaluationDimension.EVIDENCE_RAG)
        self.assertIn("provenance_completeness", res.metrics)
        self.assertEqual(res.metrics["provenance_completeness"], 1.0)

    def test_claims_runner_causal_and_citation_hygiene(self):
        """Verify Claims runner detects causal overreach and verifies citations."""
        runner = ClaimsRunner()
        case_j = next(c for c in GOLDEN_DATASET_V1.cases if c.case_id == "CASE_J_CAUSAL_OVERREACH")
        res_j = runner.evaluate_case(case_j)
        self.assertTrue(res_j.passed)
        self.assertNotIn(FailureCategory.CAUSAL_OVERREACH, res_j.failures)

    def test_intelligence_runner_contradictions_and_gaps(self):
        """Verify Intelligence runner identifies contradictions and checks qualified gap phrasing."""
        runner = IntelligenceRunner()
        case_c = next(c for c in GOLDEN_DATASET_V1.cases if c.case_id == "CASE_C_CONTRADICTORY")
        res_c = runner.evaluate_case(case_c)
        self.assertTrue(res_c.passed)
        self.assertIn("contradiction_precision", res_c.metrics)
        self.assertEqual(res_c.metrics["contradiction_precision"], 1.0)

    def test_loop_runner_efficiency_and_drift(self):
        """Verify Loop runner checks iteration efficiency and drift guard."""
        runner = LoopRunner()
        case_g = next(c for c in GOLDEN_DATASET_V1.cases if c.case_id == "CASE_G_ITERATIVE_SEARCH")
        res_g = runner.evaluate_case(case_g)
        self.assertTrue(res_g.passed)
        self.assertIn("valid_stop_reason", res_g.metrics)
        self.assertEqual(res_g.metrics["valid_stop_reason"], 1.0)

    def test_all_20_deterministic_adversarial_benchmarks(self):
        """Verify all 20 required deterministic red-team checks pass."""
        runner = AdversarialRunner()
        adv_results = runner.run_all_adversarial_tests()
        self.assertEqual(len(adv_results), 20)

        failed_adv = [r for r in adv_results if not r.passed]
        self.assertEqual(len(failed_adv), 0, f"Adversarial checks failed: {[r.case_id for r in failed_adv]}")

    def test_security_regression_runner(self):
        """Verify Stage 7 security controls remain active."""
        runner = SecurityRunner()
        case_sec = next(c for c in GOLDEN_DATASET_V1.cases if c.case_id == "CASE_A_STRAIGHTFORWARD")
        res = runner.evaluate_case(case_sec)
        self.assertTrue(res.passed)
        self.assertEqual(res.metrics.get("security_controls_active"), 1.0)

    def test_quality_gates_enforcement(self):
        """Verify quality gates correctly enforce hard thresholds."""
        mock_metrics = {
            "citation_validity": 1.0,
            "provenance_completeness": 1.0,
            "adversarial_pass_rate": 1.0,
            "security_controls_active": 1.0,
            "sufficiency_score": 1.0,
            "precision_at_5": 0.6,
            "loop_efficiency": 0.85
        }
        eval_results = evaluate_quality_gates(mock_metrics)
        for gid, gdata in eval_results.items():
            self.assertTrue(gdata["passed"], f"Gate '{gid}' failed with value {gdata['actual_value']}")

    def test_full_evaluation_run_orchestration(self):
        """Verify full evaluation run generates artifacts and passes hard quality gates."""
        run_record = execute_evaluation_run(run_id="test_harness_run")
        self.assertGreaterEqual(run_record.total_cases, 34)  # 14 golden + 20 adv + 1 sec
        self.assertEqual(run_record.final_verdict, EvaluationVerdict.PASS)
        self.assertIn("GATE_CITATION_VALIDITY", run_record.gate_results)
        self.assertTrue(run_record.gate_results["GATE_CITATION_VALIDITY"]["passed"])


if __name__ == "__main__":
    unittest.main()
