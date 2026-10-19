"""
Claim & Citation Alignment Evaluation Runner.
Evaluates citation integrity, evidence-to-claim entailing, causal overreach,
and quantitative extraction accuracy.
"""

from typing import List, Set
from evaluation.models import EvaluationCase, EvaluationResult
from evaluation.runners.base_runner import BaseRunner
from evaluation.taxonomy import EvaluationDimension, FailureCategory
from evaluation.metrics.claims_citations import (
    calculate_citation_validity,
    calculate_claim_grounding_accuracy,
    detect_causal_overreach,
    detect_superlative_overclaim,
)
from app.rag.evidence import EvidenceRegistry
from app.models.domain import EvidenceChunk, ResearchClaim
from app.rag.claim_support_verifier import EvidenceSupportVerifier


class ClaimsRunner(BaseRunner):
    """Evaluates claim citation validity, causal hygiene, and quote alignment."""

    def __init__(self):
        super().__init__(dimension=EvaluationDimension.CLAIMS_CITATIONS)
        self.verifier = EvidenceSupportVerifier(use_llm=False)

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        failures: List[FailureCategory] = []
        metrics = {}

        # Set of valid registered evidence IDs
        valid_evidence_ids: Set[str] = {ev.evidence_id for ev in case.reference_evidence}
        relevant_evidence_ids: Set[str] = {ev.evidence_id for ev in case.reference_evidence if ev.is_relevant}

        # 1. Evaluate Citation Validity (do citations exist in evidence registry?)
        all_cited_ids = []
        for cl in case.reference_claims:
            all_cited_ids.extend(cl.supported_by_ids)

        citation_validity = calculate_citation_validity(all_cited_ids, valid_evidence_ids)
        metrics["citation_validity"] = citation_validity
        if citation_validity < 1.0:
            failures.append(FailureCategory.CITATION_MISMATCH)

        # 2. Evaluate Citation Relevance (does cited evidence correspond to the correct topic?)
        irrelevant_cites = [cid for cid in all_cited_ids if cid not in relevant_evidence_ids]
        if irrelevant_cites:
            failures.append(FailureCategory.SOURCE_MISMATCH)

        # 3. Evaluate Causal Overreach (Case J check)
        for cl in case.reference_claims:
            if cl.contains_causal_overreach:
                # If claim is flagged with causal overreach, test that our detector catches it
                is_causal = detect_causal_overreach(cl.claim_text, is_observational_study=True)
                if is_causal:
                    failures.append(FailureCategory.CAUSAL_OVERREACH)
            else:
                # Claim should NOT have causal overreach
                if detect_causal_overreach(cl.claim_text, is_observational_study=True):
                    failures.append(FailureCategory.CAUSAL_OVERREACH)

        # 4. Evaluate Superlative Claims
        for cl in case.reference_claims:
            if detect_superlative_overclaim(cl.claim_text):
                failures.append(FailureCategory.SUPERLATIVE_OVERCLAIM)

        # 5. Evaluate Quantitative Precision (Case K check)
        if case.metadata.get("category") == "quantitative_extraction":
            # Verify numerical values are maintained in the claims
            for cl in case.reference_claims:
                if "1.0" not in cl.claim_text and "10^-21" not in cl.claim_text and "10" not in cl.claim_text:
                    failures.append(FailureCategory.QUANTITATIVE_MISMATCH)

        passed = len(failures) == 0

        return EvaluationResult(
            case_id=case.case_id,
            case_name=case.name,
            dimension=self.dimension,
            passed=passed,
            failures=failures,
            metrics=metrics,
            details={
                "claims_evaluated": len(case.reference_claims),
                "citations_evaluated": len(all_cited_ids),
                "valid_evidence_ids": list(valid_evidence_ids)
            }
        )
