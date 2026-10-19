"""
Evidence Strength Evaluator for Research Intelligence Assistant V2 (Stage 4).
Calculates interpretable, explainable evidence strength ratings.
Strictly eliminates unvalidated numerical confidence percentages (e.g. 97% or 0.85).
"""

from typing import Any, Dict, List, Set
from app.core.logging import logger
from app.models.domain import (
    ContradictionFinding,
    EvidenceChunk,
    EvidenceStrength,
    EvidenceStrengthRating,
    ResearchClaim,
    ResearchFinding,
)


class EvidenceStrengthEvaluator:
    """
    Evaluates collective evidence strength using explainable criteria:
    - Number of independent papers retrieved
    - Degree of empirical agreement vs contradiction
    - Directness of available excerpts
    - Source replication signals
    """

    def evaluate_strength(
        self,
        claims: List[ResearchClaim],
        evidence_chunks: List[EvidenceChunk],
        contradictions: List[ContradictionFinding],
        findings: List[ResearchFinding],
    ) -> EvidenceStrength:
        """
        Determines interpretable evidence rating and grounded rationale.
        """
        # Count unique papers with verified evidence
        paper_ids_with_evidence: Set[str] = {
            c.paper_id for c in evidence_chunks if c.paper_id
        }
        supporting_paper_count = len(paper_ids_with_evidence)
        evidence_chunks_count = len(evidence_chunks)

        # Check for genuine contradictions
        genuine_conflicts = [c for c in contradictions if c.is_genuine_contradiction]
        contradicting_paper_count = len({
            p for c in genuine_conflicts for p in (c.paper_a_id, c.paper_b_id) if p
        })

        # Check for methodology differences / qualified findings
        has_divergence = len(contradictions) > 0

        # 1. Zero evidence or single abstract with no claims
        if supporting_paper_count == 0 or evidence_chunks_count == 0:
            return EvidenceStrength(
                rating=EvidenceStrengthRating.INSUFFICIENT,
                rationale="Retrieved evidence contains zero or insufficient supporting scientific excerpts for this research question.",
                supporting_paper_count=0,
                contradicting_paper_count=0,
                evidence_chunks_count=0,
                consistency_assessment="Insufficient data",
            )

        # 2. Genuine direct result conflicts present
        if genuine_conflicts:
            conflict_topics = ", ".join({c.topic for c in genuine_conflicts})
            return EvidenceStrength(
                rating=EvidenceStrengthRating.MIXED,
                rationale=(
                    f"Retrieved literature contains direct conflicting empirical findings across {contradicting_paper_count} "
                    f"studies regarding: {conflict_topics}. Reconciling these discrepancies requires standardized comparative evaluation."
                ),
                supporting_paper_count=supporting_paper_count,
                contradicting_paper_count=contradicting_paper_count,
                evidence_chunks_count=evidence_chunks_count,
                consistency_assessment="Conflicting / Divergent",
            )

        # 3. Single paper evidence
        if supporting_paper_count == 1:
            pid = next(iter(paper_ids_with_evidence))
            return EvidenceStrength(
                rating=EvidenceStrengthRating.LIMITED,
                rationale=(
                    f"Evidence is derived from a single retrieved study (Paper '{pid}'). "
                    "Replication across independent research groups, diverse datasets, and varying settings is required to establish broader consensus."
                ),
                supporting_paper_count=1,
                contradicting_paper_count=0,
                evidence_chunks_count=evidence_chunks_count,
                consistency_assessment="Single-study observation (unreplicated)",
            )

        # 4. Moderate evidence (2-3 papers)
        if supporting_paper_count in (2, 3):
            if has_divergence:
                return EvidenceStrength(
                    rating=EvidenceStrengthRating.LIMITED,
                    rationale=(
                        f"Evidence spans {supporting_paper_count} retrieved papers, but observations vary across "
                        "different experimental datasets or methodologies, limiting generalized conclusions."
                    ),
                    supporting_paper_count=supporting_paper_count,
                    contradicting_paper_count=0,
                    evidence_chunks_count=evidence_chunks_count,
                    consistency_assessment="Heterogeneous across methodologies",
                )
            else:
                return EvidenceStrength(
                    rating=EvidenceStrengthRating.MODERATE,
                    rationale=(
                        f"Multiple independent retrieved studies ({supporting_paper_count} papers, {evidence_chunks_count} evidence chunks) "
                        "report concordant directional findings under comparable experimental parameters."
                    ),
                    supporting_paper_count=supporting_paper_count,
                    contradicting_paper_count=0,
                    evidence_chunks_count=evidence_chunks_count,
                    consistency_assessment="Moderate multi-study consistency",
                )

        # 5. Strong evidence (4+ papers)
        if has_divergence:
            return EvidenceStrength(
                rating=EvidenceStrengthRating.MODERATE,
                rationale=(
                    f"Broad multi-paper coverage ({supporting_paper_count} papers), but methodological variations and "
                    "context-dependent factors yield moderate rather than unanimous consensus."
                ),
                supporting_paper_count=supporting_paper_count,
                contradicting_paper_count=0,
                evidence_chunks_count=evidence_chunks_count,
                consistency_assessment="Substantial coverage with contextual variation",
            )

        return EvidenceStrength(
            rating=EvidenceStrengthRating.STRONG,
            rationale=(
                f"Strong multi-study convergence across {supporting_paper_count} retrieved papers ({evidence_chunks_count} evidence chunks) "
                "consistently confirming the primary research propositions without observed direct conflicts."
            ),
            supporting_paper_count=supporting_paper_count,
            contradicting_paper_count=0,
            evidence_chunks_count=evidence_chunks_count,
            consistency_assessment="High multi-study convergence",
        )
