"""
Stage 3 RAG & Evidence Grounding Evaluation Runner.
Evaluates evidence chunking, provenance completeness, and claim-to-evidence support verdicts.
"""

from typing import List
from evaluation.models import EvaluationCase, EvaluationResult
from evaluation.runners.base_runner import BaseRunner
from evaluation.taxonomy import EvaluationDimension, FailureCategory
from evaluation.metrics.evidence_rag import (
    calculate_evidence_relevance,
    calculate_provenance_completeness,
    calculate_evidence_sufficiency,
    calculate_unsupported_claim_rate,
)
from app.models.domain import EvidenceChunk, ResearchClaim
from app.rag.evidence import EvidenceRegistry
from app.rag.claim_support_verifier import EvidenceSupportVerifier


class RagRunner(BaseRunner):
    """Evaluates Stage 3 RAG evidence extraction, provenance, and support verdicts."""

    def __init__(self):
        super().__init__(dimension=EvaluationDimension.EVIDENCE_RAG)
        self.verifier = EvidenceSupportVerifier(use_llm=False)

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        failures: List[FailureCategory] = []
        metrics = {}

        # 1. Build and populate Registry from reference evidence
        registry = EvidenceRegistry(run_id=f"eval_rag_{case.case_id}")
        raw_evidence_items = []

        for idx, ref_ev in enumerate(case.reference_evidence, start=1):
            chunk = EvidenceChunk(
                chunk_id=f"chk_{case.case_id}_{idx}",
                paper_id=f"pap_{case.case_id}_{idx}",
                evidence_id=ref_ev.evidence_id,
                title=ref_ev.paper_title,
                authors=["Author A", "Author B"],
                year=2021,
                venue="Journal of Science",
                source_url=ref_ev.source_url or "https://doi.org/10.000/eval",
                doi=ref_ev.doi,
                text=ref_ev.text_snippet,
                section=ref_ev.section,
                relevance_score=1.0 if ref_ev.is_relevant else 0.1
            )
            registry.register(chunk)
            raw_evidence_items.append(chunk.model_dump())

        # 2. Compute provenance completeness
        prov_completeness = calculate_provenance_completeness(raw_evidence_items)
        metrics["provenance_completeness"] = prov_completeness
        if prov_completeness < 0.9:
            failures.append(FailureCategory.SOURCE_MISMATCH)

        # 3. Compute evidence relevance
        keywords = case.research_question.split()[:5]
        snippets = [ev.text_snippet for ev in case.reference_evidence if ev.is_relevant]
        ev_relevance = calculate_evidence_relevance(snippets, keywords)
        metrics["evidence_relevance"] = ev_relevance

        # 4. Verify claim support for reference claims
        claim_verdicts = []
        for ref_claim in case.reference_claims:
            rc = ResearchClaim(
                claim_id=ref_claim.claim_id,
                claim_text=ref_claim.claim_text,
                citing_evidence_ids=ref_claim.supported_by_ids,
                support_status="UNSUPPORTED"
            )

            # Look up citing chunks in registry
            chunks = [registry.get(eid) for eid in ref_claim.supported_by_ids if registry.get(eid)]
            if not chunks:
                failures.append(FailureCategory.EVIDENCE_MISMATCH)
                continue

            result = self.verifier.verify_claim_support(rc, chunks)
            actual_verdict = result.verdict.value.upper()
            expected_verdict = ref_claim.expected_status.upper()
            claim_verdicts.append({"claim_id": rc.claim_id, "actual": actual_verdict, "expected": expected_verdict})

            # Check verdict alignment
            if actual_verdict != expected_verdict:
                if actual_verdict == "UNSUPPORTED":
                    failures.append(FailureCategory.UNSUPPORTED_CLAIM)
                elif actual_verdict == "PARTIALLY_SUPPORTED" and expected_verdict == "SUPPORTED":
                    failures.append(FailureCategory.PARTIAL_SUPPORT)
                else:
                    failures.append(FailureCategory.EVIDENCE_MISMATCH)

        # 5. Measure evidence sufficiency against expected case verdict
        if case.expected_verdict:
            last_verdict = claim_verdicts[-1]["actual"] if claim_verdicts else "UNSUPPORTED"
            sufficiency_score = calculate_evidence_sufficiency(last_verdict, case.expected_verdict)
            metrics["sufficiency_score"] = sufficiency_score
            if sufficiency_score < 1.0:
                failures.append(FailureCategory.EVIDENCE_MISMATCH)

        passed = len(failures) == 0

        return EvaluationResult(
            case_id=case.case_id,
            case_name=case.name,
            dimension=self.dimension,
            passed=passed,
            failures=failures,
            metrics=metrics,
            details={
                "claim_verdicts": claim_verdicts,
                "evidence_count": len(case.reference_evidence)
            }
        )
