"""
Base Evaluation Runner.
Provides standardized timing, error isolation, secret scrubbing, and reporting primitives.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from evaluation.models import EvaluationCase, EvaluationResult
from evaluation.taxonomy import EvaluationDimension, FailureCategory


class BaseRunner(ABC):
    """Abstract base class for all dimensional evaluation runners."""

    def __init__(self, dimension: EvaluationDimension):
        self.dimension = dimension

    @abstractmethod
    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        """Executes evaluation for a single test case."""
        pass

    def run_suite(self, cases: List[EvaluationCase]) -> List[EvaluationResult]:
        """Executes evaluation across a filtered list of test cases."""
        results = []
        for case in cases:
            if case.dimension == self.dimension or self.dimension == EvaluationDimension.ADVERSARIAL:
                results.append(self.safe_evaluate(case))
        return results

    def safe_evaluate(self, case: EvaluationCase) -> EvaluationResult:
        """Wraps case evaluation with error handling and duration tracking."""
        start = time.time()
        try:
            res = self.evaluate_case(case)
            res.duration_seconds = round(time.time() - start, 4)
            return res
        except Exception as err:
            duration = round(time.time() - start, 4)
            return EvaluationResult(
                case_id=case.case_id,
                case_name=case.name,
                dimension=self.dimension,
                passed=False,
                failures=[FailureCategory.STRUCTURED_OUTPUT_FAILURE],
                duration_seconds=duration,
                details={"error": str(err)},
                notes=f"Runner execution exception: {err}"
            )
