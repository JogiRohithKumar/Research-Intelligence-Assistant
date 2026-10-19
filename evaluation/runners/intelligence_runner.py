"""
Stage 4 Research Intelligence Evaluation Runner.
Evaluates cross-paper comparison extraction, contradiction detection fidelity,
qualified research gap phrasing, and qualitative evidence strength classification.
"""

from typing import Any, Dict, List
from evaluation.models import EvaluationCase, EvaluationResult
from evaluation.runners.base_runner import BaseRunner
from evaluation.taxonomy import EvaluationDimension, FailureCategory
from evaluation.metrics.intelligence import (
    calculate_contradiction_precision,
    calculate_gap_qualification_rate,
    verify_evidence_strength_heuristic,
)
from app.agents.research_intelligence_agent import generate_research_intelligence
from app.models.domain import EvidenceChunk, ResearchClaim


class IntelligenceRunner(BaseRunner):
    """Evaluates Stage 4 intelligence engine on comparisons, contradictions, and gaps."""

    def __init__(self):
        super().__init__(dimension=EvaluationDimension.RESEARCH_INTELLIGENCE)

    def evaluate_case(self, case: EvaluationCase) -> EvaluationResult:
        failures: List[FailureCategory] = []
        metrics = {}

        # 1. Prepare papers and evidence chunks from reference data
        papers = []
        evidence_chunks = []
        for idx, ev in enumerate(case.reference_evidence, start=1):
            pid = f"paper_{case.case_id}_{idx}"
            papers.append({
                "paper_id": pid,
                "title": ev.paper_title,
                "abstract": ev.text_snippet,
                "authors": ["Lead Researcher", "Co-Author"],
                "year": 2022,
                "venue": "Academic Review"
            })
            evidence_chunks.append(
                EvidenceChunk(
                    evidence_id=ev.evidence_id,
                    paper_id=pid,
                    chunk_id=f"chk_{pid}_0",
                    title=ev.paper_title,
                    text=ev.text_snippet,
                    authors=["Lead Researcher", "Co-Author"],
                    year=2022,
                    source_url=ev.source_url or "https://doi.org/10.000/eval",
                    doi=ev.doi,
                    relevance_score=1.0 if ev.is_relevant else 0.1
                )
            )

        claims = []
        for c in case.reference_claims:
            source_pids = [
                f"paper_{case.case_id}_{idx}"
                for idx, ev in enumerate(case.reference_evidence, start=1)
                if ev.evidence_id in c.supported_by_ids
            ]
            claims.append({
                "claim_id": c.claim_id,
                "claim_text": c.claim_text,
                "evidence_ids": c.supported_by_ids,
                "source_paper_ids": source_pids,
                "support_status": "SUPPORTED" if c.expected_status.upper() == "SUPPORTED" else "UNSUPPORTED"
            })

        # 2. Execute Stage 4 Research Intelligence
        intel = generate_research_intelligence(
            query=case.research_question,
            papers=papers,
            evidence_registry=[c.model_dump() for c in evidence_chunks],
            claims=claims
        )

        study_comparisons = intel.get("comparisons") or intel.get("study_comparisons") or []
        contradictions = intel.get("contradictions") or intel.get("contradiction_findings") or []
        gaps = intel.get("gaps") or intel.get("research_gaps") or []
        evidence_strength = intel.get("evidence_strength") or {}
        consensus = intel.get("consensus_synthesis") or {}

        # 3. Contradiction Detection Evaluation
        expected_contradiction = bool(case.metadata.get("expected_contradictions", 0) > 0 or case.case_id in {"CASE_C_CONTRADICTORY", "CASE_M_GENUINE_DISAGREEMENT"})
        contra_precision = calculate_contradiction_precision(contradictions, expected_contradiction)
        metrics["contradiction_precision"] = contra_precision
        if expected_contradiction and not contradictions:
            failures.append(FailureCategory.CONTRADICTION_MISCLASSIFICATION)

        # 4. Research Gap Framing Evaluation (Case E check)
        gap_qual_rate = calculate_gap_qualification_rate(gaps)
        metrics["gap_qualification_rate"] = gap_qual_rate
        if gap_qual_rate < 0.7:
            failures.append(FailureCategory.GAP_OVERCLAIM)

        # 5. Evidence Strength Classification Rules
        rating = evidence_strength.get("rating") if isinstance(evidence_strength, dict) else str(evidence_strength)
        study_types = [p["abstract"] for p in papers]
        strength_valid = verify_evidence_strength_heuristic(rating or "MODERATE", study_types)
        metrics["evidence_strength_conformance"] = 1.0 if strength_valid else 0.0

        # 6. Consensus Overclaim Check (Sparse literature should not declare strong consensus)
        if case.case_id in {"CASE_F_SPARSE_LIT", "CASE_N_INSUFFICIENT_EVIDENCE"}:
            cons_type = (consensus.get("consensus_type") if isinstance(consensus, dict) else "").upper()
            if cons_type in {"STRONG_CONSENSUS", "UNANIMOUS", "ESTABLISHED"}:
                failures.append(FailureCategory.CONSENSUS_OVERCLAIM)

        passed = len(failures) == 0

        return EvaluationResult(
            case_id=case.case_id,
            case_name=case.name,
            dimension=self.dimension,
            passed=passed,
            failures=failures,
            metrics=metrics,
            details={
                "comparisons_count": len(study_comparisons),
                "contradictions_count": len(contradictions),
                "gaps_count": len(gaps),
                "evidence_strength": rating
            }
        )
