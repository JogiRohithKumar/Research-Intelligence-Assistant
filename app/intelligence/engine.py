"""
Research Intelligence Engine for Research Intelligence Assistant V2 (Stage 4).
Orchestrates the complete Stage 4 research intelligence pipeline:
Methodology comparison, contradiction detection, cross-paper analysis,
evidence strength evaluation, research gap detection, and consensus synthesis.
"""

from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.intelligence.consensus_synthesizer import ConsensusSynthesizer
from app.intelligence.contradiction_detector import ContradictionDetector
from app.intelligence.cross_paper_analyzer import CrossPaperAnalyzer
from app.intelligence.evidence_strength_evaluator import EvidenceStrengthEvaluator
from app.intelligence.methodology_comparator import MethodologyComparator
from app.intelligence.provenance_guard import ProvenanceGuard
from app.intelligence.research_gap_detector import ResearchGapDetector
from app.models.domain import (
    ConsensusSynthesis,
    ContradictionFinding,
    EvidenceChunk,
    EvidenceStrength,
    FindingType,
    PaperComparison,
    ResearchClaim,
    ResearchFinding,
    ResearchGapFinding,
    ResearchIntelligenceReport,
)


class ResearchIntelligenceEngine:
    """
    Authoritative coordinator for Stage 4 Research Intelligence.
    Consumes Stage 3 validated claims and EvidenceChunks.
    Guarantees that no intelligence outruns the evidence layer.
    """

    def analyze(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        evidence_chunks: List[EvidenceChunk],
        claims: List[ResearchClaim],
    ) -> Dict[str, Any]:
        """
        Executes end-to-end research intelligence analysis with full provenance.
        """
        logger.info(
            f"Initiating Stage 4 Research Intelligence for query: '{query}' "
            f"({len(papers)} candidate papers, {len(evidence_chunks)} evidence chunks, {len(claims)} validated claims)"
        )

        # 1. Methodology Comparison
        comparator = MethodologyComparator()
        raw_comparisons = comparator.compare_papers(papers, evidence_chunks)

        # 2. Contradiction Detection
        contradiction_detector = ContradictionDetector(evidence_chunks)
        raw_contradictions = contradiction_detector.detect_contradictions(claims, raw_comparisons)

        # 3. Cross-Paper Findings (Agreement / Disagreement / Qualification)
        cross_analyzer = CrossPaperAnalyzer(evidence_chunks)
        raw_findings = cross_analyzer.analyze_cross_paper(claims, raw_comparisons, raw_contradictions, query)

        # 4. Evidence Strength Assessment
        strength_evaluator = EvidenceStrengthEvaluator()
        evidence_strength = strength_evaluator.evaluate_strength(
            claims=claims,
            evidence_chunks=evidence_chunks,
            contradictions=raw_contradictions,
            findings=raw_findings,
        )

        # 5. Research Gap Detection
        gap_detector = ResearchGapDetector(evidence_chunks)
        raw_gaps = gap_detector.detect_gaps(raw_comparisons, claims, query)

        # 6. Consensus Synthesis
        consensus_synthesizer = ConsensusSynthesizer()
        consensus = consensus_synthesizer.synthesize_consensus(
            query=query,
            findings=raw_findings,
            contradictions=raw_contradictions,
            comparisons=raw_comparisons,
            evidence_strength=evidence_strength,
            gaps=raw_gaps,
            evidence_chunks=evidence_chunks,
        )

        # 7. Provenance Guard & Audit (Hard filter against hallucinated IDs)
        provenance_guard = ProvenanceGuard(
            evidence_chunks=evidence_chunks,
            claims=claims,
            candidate_papers=papers,
        )
        audit_result = provenance_guard.audit_and_filter_findings(
            findings=raw_findings,
            comparisons=raw_comparisons,
            contradictions=raw_contradictions,
            gaps=raw_gaps,
        )

        validated_findings: List[ResearchFinding] = audit_result["findings"]
        validated_comparisons: List[PaperComparison] = audit_result["comparisons"]
        validated_contradictions: List[ContradictionFinding] = audit_result["contradictions"]
        validated_gaps: List[ResearchGapFinding] = audit_result["gaps"]
        audit_summary: Dict[str, Any] = audit_result["audit_summary"]

        # Structured Observability Logging
        for f in validated_findings:
            logger.info(
                f"[Stage 4 Log] finding_id={f.finding_id} type={f.finding_type.value} "
                f"papers={f.paper_ids} evidence={f.evidence_ids} status={f.support_status.value} "
                f"strength={evidence_strength.rating.value}"
            )

        # Build Stage 4 typed report
        report_model = ResearchIntelligenceReport(
            findings=validated_findings,
            comparisons=validated_comparisons,
            contradictions=validated_contradictions,
            gaps=validated_gaps,
            consensus=consensus,
            evidence_strength=evidence_strength,
            provenance_audit=audit_summary,
        )

        # Prepare backward-compatible dictionaries for existing nodes/tests
        common_findings = [
            f.finding_text for f in validated_findings if f.finding_type in (FindingType.AGREEMENT, FindingType.CONSENSUS)
        ] or [consensus.synthesis_statement]

        conflicting_findings = [
            f"{c.topic}: {c.claim_a} vs {c.claim_b} (Type: {c.contradiction_type.value})"
            for c in validated_contradictions
        ]

        legacy_verification = {
            "common_findings": common_findings,
            "conflicting_findings": conflicting_findings,
            "evidence_strength": evidence_strength.rating.value.lower(),
            "confidence_score": 0.0,  # Zero fake confidence score
            "strength_rationale": evidence_strength.rationale,
            "consistency_assessment": evidence_strength.consistency_assessment,
        }

        legacy_gaps = {
            "research_gaps": [g.description for g in validated_gaps],
            "missing_areas": [
                f"[{g.category.value}] {g.description}" for g in validated_gaps
            ],
            "future_directions": [
                f"Address {g.category.value.lower()}: {g.reasoning}" for g in validated_gaps
            ],
            "unanswered_questions": [
                f"How do findings generalize across unstudied settings identified in {g.gap_id}?"
                for g in validated_gaps
            ],
        }

        # Serialized collections for state & API
        return {
            "report_model": report_model,
            "findings": [f.model_dump() for f in validated_findings],
            "comparisons": [c.model_dump() for c in validated_comparisons],
            "contradictions": [c.model_dump() for c in validated_contradictions],
            "gaps": [g.model_dump() for g in validated_gaps],
            "consensus": consensus.model_dump(),
            "evidence_strength": evidence_strength.model_dump(),
            "provenance_audit": audit_summary,
            # Legacy compatibility mappings
            "verification": legacy_verification,
            "legacy_gaps": legacy_gaps,
            "paper_count": len(papers),
            "evidence_count": len(evidence_chunks),
            "claim_count": len(claims),
        }
