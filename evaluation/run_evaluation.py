"""
Main Evaluation Orchestrator for Stage 8.
Runs comprehensive evaluations across all dimensions, computes quality gates,
records failure taxonomy breakdowns, and generates authoritative JSON/Markdown artifacts.
"""

import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from evaluation.datasets.golden_dataset import GOLDEN_DATASET_V1
from evaluation.models import EvaluationCase, EvaluationResult, EvaluationRun, MetricResult
from evaluation.quality_gates import QUALITY_GATES, evaluate_quality_gates
from evaluation.reporters.json_reporter import save_json_report
from evaluation.reporters.markdown_reporter import generate_markdown_report
from evaluation.runners import (
    AdversarialRunner,
    ClaimsRunner,
    IntelligenceRunner,
    LoopRunner,
    RagRunner,
    RetrievalRunner,
    SecurityRunner,
)
from evaluation.taxonomy import EvaluationDimension, EvaluationVerdict, QualityGateType


def execute_evaluation_run(run_id: Optional[str] = None) -> EvaluationRun:
    """
    Executes the authoritative Stage 8 evaluation run.
    Evaluates:
      1. Golden Dataset Cases A-N across Retrieval, RAG, Claims, Intelligence, Loop
      2. 20 Deterministic Adversarial Red-Team Checks
      3. Stage 7 Security Regression Suite
    """
    start_time = time.time()
    effective_run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"

    # Instantiate dimensional runners
    retrieval_runner = RetrievalRunner()
    rag_runner = RagRunner()
    claims_runner = ClaimsRunner()
    intelligence_runner = IntelligenceRunner()
    loop_runner = LoopRunner()
    adversarial_runner = AdversarialRunner()
    security_runner = SecurityRunner()

    all_case_results: List[EvaluationResult] = []
    failures_by_category: Dict[str, int] = {}

    # 1. Evaluate Golden Dataset Cases A through N
    for case in GOLDEN_DATASET_V1.cases:
        if case.dimension == EvaluationDimension.RETRIEVAL:
            res = retrieval_runner.safe_evaluate(case)
        elif case.dimension == EvaluationDimension.EVIDENCE_RAG:
            res = rag_runner.safe_evaluate(case)
        elif case.dimension == EvaluationDimension.CLAIMS_CITATIONS:
            res = claims_runner.safe_evaluate(case)
        elif case.dimension == EvaluationDimension.RESEARCH_INTELLIGENCE:
            res = intelligence_runner.safe_evaluate(case)
        elif case.dimension == EvaluationDimension.AGENTIC_LOOP:
            res = loop_runner.safe_evaluate(case)
        else:
            res = rag_runner.safe_evaluate(case)

        all_case_results.append(res)
        for f in res.failures:
            failures_by_category[f.value] = failures_by_category.get(f.value, 0) + 1

    # 2. Evaluate 20 Deterministic Adversarial Red-Team Checks
    adv_results = adversarial_runner.run_all_adversarial_tests()
    all_case_results.extend(adv_results)
    for res in adv_results:
        for f in res.failures:
            failures_by_category[f.value] = failures_by_category.get(f.value, 0) + 1

    # 3. Evaluate Security Regression Check
    dummy_sec_case = EvaluationCase(
        case_id="SEC_REGRESSION_01",
        name="Stage 7 Security Controls Verification",
        dimension=EvaluationDimension.SECURITY_REGRESSION,
        research_question="Verify zero security regressions across auth, tokens, and headers",
        expected_behavior="All Stage 7 security features remain 100% active"
    )
    sec_res = security_runner.safe_evaluate(dummy_sec_case)
    all_case_results.append(sec_res)
    for f in sec_res.failures:
        failures_by_category[f.value] = failures_by_category.get(f.value, 0) + 1

    # 4. Aggregate Metrics Across Cases
    passed_cases = sum(1 for r in all_case_results if r.passed)
    failed_cases = len(all_case_results) - passed_cases
    total_cases = len(all_case_results)

    aggregated_metrics: Dict[str, float] = {}
    metric_counts: Dict[str, int] = {}

    for r in all_case_results:
        for k, v in r.metrics.items():
            aggregated_metrics[k] = aggregated_metrics.get(k, 0.0) + float(v)
            metric_counts[k] = metric_counts.get(k, 0) + 1

    # Average metrics
    averaged_metrics: Dict[str, float] = {}
    for k, v in aggregated_metrics.items():
        averaged_metrics[k] = round(v / max(1, metric_counts[k]), 4)

    # Add adversarial pass rate
    passed_adv = sum(1 for r in adv_results if r.passed)
    averaged_metrics["adversarial_pass_rate"] = round(passed_adv / max(1, len(adv_results)), 4)
    averaged_metrics["security_controls_active"] = 1.0 if sec_res.passed else 0.0

    # 5. Evaluate Quality Gates
    gate_evals = evaluate_quality_gates(averaged_metrics)

    # 6. Format Metric Results
    metric_results = []
    for gid, gdata in gate_evals.items():
        metric_results.append(
            MetricResult(
                metric_name=gdata["metric_name"],
                dimension=EvaluationDimension(gdata["dimension"]),
                value=gdata["actual_value"],
                threshold=gdata["threshold"],
                passed=gdata["passed"],
                gate_type=QualityGateType(gdata["gate_type"]),
                rationale=gdata["rationale"]
            )
        )

    # 7. Determine Final Verdict
    hard_gates_failed = [
        gid for gid, g in gate_evals.items()
        if g["gate_type"] == QualityGateType.HARD.value and not g["passed"]
    ]

    duration = round(time.time() - start_time, 2)
    final_verdict = EvaluationVerdict.PASS if not hard_gates_failed else EvaluationVerdict.HOLD

    run = EvaluationRun(
        run_id=effective_run_id,
        code_version="1.0.0",
        dataset_version=GOLDEN_DATASET_V1.version,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        case_results=all_case_results,
        metric_results=metric_results,
        gate_results=gate_evals,
        failures_by_category=failures_by_category,
        duration_seconds=duration,
        final_verdict=final_verdict,
        environment={"os": sys.platform, "python_version": sys.version.split()[0]}
    )

    # 8. Persist Reports
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    save_json_report(run, output_dir=reports_dir)
    generate_markdown_report(run, output_path=reports_dir / f"evaluation_run_{effective_run_id}.md")

    return run


if __name__ == "__main__":
    print("Executing Stage 8 Evaluation Run...")
    run_record = execute_evaluation_run()
    print(f"Evaluation Run Completed in {run_record.duration_seconds}s")
    print(f"Total Cases: {run_record.total_cases} | Passed: {run_record.passed_cases} | Failed: {run_record.failed_cases}")
    print(f"Final Verdict: {run_record.final_verdict.value}")
    if run_record.failures_by_category:
        print("Failure Taxonomy Breakdown:")
        for cat, cnt in run_record.failures_by_category.items():
            print(f"  - {cat}: {cnt}")
