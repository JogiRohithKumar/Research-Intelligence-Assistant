"""
Stage 2 Retrieval Evaluation Runner.
Executes retrieval benchmarks against the Stage 2 ResearchSearchEngine,
measuring Precision@K, Recall@K, Hit@K, MRR, duplicate rate, and distractor rejection.
"""

from typing import List
from evaluation.models import EvaluationCase, EvaluationResult
from evaluation.runners.base_runner import BaseRunner
from evaluation.taxonomy import EvaluationDimension, FailureCategory
from evaluation.metrics.retrieval import (
    calculate_hit_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mrr,
    calculate_duplicate_rate,
    calculate_irrelevant_rate,
)
from app.agents.search_agent import get_search_engine, search_papers


class RetrievalRunner(BaseRunner):
    """Evaluates Stage 2 academic search, multi-provider retrieval, and deduplication."""

    def __init__(self):
        super().__init__(dimension=EvaluationDimension.RETRIEVAL)
        self.engine = get_search_engine()

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        query = case.research_question
        expected_titles = [ev.paper_title for ev in case.reference_evidence if ev.is_relevant]
        irrelevant_titles = [ev.paper_title for ev in case.reference_evidence if not ev.is_relevant]

        failures: List[FailureCategory] = []
        metrics = {}

        try:
            # Execute real Stage 2 retrieval
            retrieved_papers = search_papers(query=query, limit=10)
            retrieved_titles = [p.get("title", "") for p in retrieved_papers if p.get("title")]

            # Calculate metrics
            hit_at_5 = calculate_hit_at_k(retrieved_titles, expected_titles, k=5)
            precision_at_5 = calculate_precision_at_k(retrieved_titles, expected_titles, k=5)
            recall_at_5 = calculate_recall_at_k(retrieved_titles, expected_titles, k=5)
            mrr = calculate_mrr(retrieved_titles, expected_titles)
            dup_rate = calculate_duplicate_rate(retrieved_titles)
            irr_rate = calculate_irrelevant_rate(retrieved_titles, irrelevant_titles)

            metrics["hit_at_5"] = hit_at_5
            metrics["precision_at_5"] = precision_at_5
            metrics["recall_at_5"] = recall_at_5
            metrics["mrr"] = mrr
            metrics["duplicate_rate"] = dup_rate
            metrics["irrelevant_rate"] = irr_rate

            # Failure taxonomy checks
            if expected_titles and hit_at_5 == 0.0:
                failures.append(FailureCategory.RETRIEVAL_MISS)

            if dup_rate > 0.0:
                failures.append(FailureCategory.DUPLICATE_RETRIEVAL)

            if irr_rate > 0.2:
                failures.append(FailureCategory.IRRELEVANT_RETRIEVAL)

            passed = len(failures) == 0

            return EvaluationResult(
                case_id=case.case_id,
                case_name=case.name,
                dimension=self.dimension,
                passed=passed,
                failures=failures,
                metrics=metrics,
                details={
                    "retrieved_count": len(retrieved_papers),
                    "retrieved_sample": retrieved_titles[:3],
                    "expected_titles": expected_titles
                }
            )

        except Exception as err:
            return EvaluationResult(
                case_id=case.case_id,
                case_name=case.name,
                dimension=self.dimension,
                passed=False,
                failures=[FailureCategory.PROVIDER_FAILURE],
                metrics={"hit_at_5": 0.0, "mrr": 0.0},
                details={"error": str(err)},
                notes=f"Retrieval provider error: {err}"
            )
