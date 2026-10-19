"""
Consensus Synthesizer for Research Intelligence Assistant V2 (Stage 4).
Synthesizes grounded collective findings from Stage 4 structured intelligence.
Strictly handles insufficient evidence and conflicting literature without fabricating consensus.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.models.domain import (
    ConsensusSynthesis,
    ContradictionFinding,
    EvidenceChunk,
    EvidenceStrength,
    EvidenceStrengthRating,
    PaperComparison,
    ResearchFinding,
    ResearchGapFinding,
)
from app.services.llm_service import generate_structured_output


class LLMConsensusOutput(BaseModel):
    synthesis_statement: str = Field(..., description="Grounded multi-paper synthesis narrative")
    divergent_points: List[str] = Field(default_factory=list, description="Explicit points of methodological or empirical divergence")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence IDs")


class ConsensusSynthesizer:
    """
    Synthesizes the collective research findings from verified Stage 4 analytical models.
    Operates strictly upon structured findings, contradictions, and evidence strength.
    """

    def synthesize_consensus(
        self,
        query: str,
        findings: List[ResearchFinding],
        contradictions: List[ContradictionFinding],
        comparisons: List[PaperComparison],
        evidence_strength: EvidenceStrength,
        gaps: List[ResearchGapFinding],
        evidence_chunks: List[EvidenceChunk],
    ) -> ConsensusSynthesis:
        """
        Generates ConsensusSynthesis respecting evidence boundaries.
        """
        all_eids = [c.evidence_id for c in evidence_chunks]

        # 1. Handle INSUFFICIENT evidence immediately
        if evidence_strength.rating == EvidenceStrengthRating.INSUFFICIENT:
            return ConsensusSynthesis(
                consensus_status="INSUFFICIENT_EVIDENCE",
                synthesis_statement=(
                    "The retrieved evidence is insufficient to establish a reliable consensus. "
                    "The literature base returned zero or inadequate empirical evidence for this query."
                ),
                divergent_points=["Insufficient empirical literature to assess convergence or divergence."],
                evidence_strength=evidence_strength,
                supporting_evidence_ids=[],
            )

        # 2. Handle MIXED evidence (genuine contradictions present)
        if evidence_strength.rating == EvidenceStrengthRating.MIXED:
            divergent = [
                f"Paper '{ct.paper_a_id}' vs Paper '{ct.paper_b_id}': {ct.topic} ({ct.claim_a} vs {ct.claim_b})"
                for ct in contradictions if ct.is_genuine_contradiction
            ]
            return ConsensusSynthesis(
                consensus_status="MIXED",
                synthesis_statement=(
                    "The retrieved literature exhibits mixed and conflicting findings. "
                    "Studies evaluate comparable interventions under similar conditions but report opposing or incompatible results. "
                    "No scientific consensus exists across the retrieved evidence."
                ),
                divergent_points=divergent or ["Conflicting directional outcomes observed across retrieved studies."],
                evidence_strength=evidence_strength,
                supporting_evidence_ids=all_eids[:5],
            )

        # 3. Handle LIMITED, MODERATE, or STRONG evidence
        consensus_status = "ESTABLISHED" if evidence_strength.rating == EvidenceStrengthRating.STRONG else "EMERGING"

        try:
            return self._llm_synthesize(
                query=query,
                findings=findings,
                contradictions=contradictions,
                comparisons=comparisons,
                evidence_strength=evidence_strength,
                consensus_status=consensus_status,
                all_eids=all_eids,
            )
        except Exception as e:
            logger.info(f"LLM consensus synthesis fallback: {e}")
            return self._heuristic_synthesize(
                query=query,
                findings=findings,
                contradictions=contradictions,
                evidence_strength=evidence_strength,
                consensus_status=consensus_status,
                all_eids=all_eids,
            )

    def _llm_synthesize(
        self,
        query: str,
        findings: List[ResearchFinding],
        contradictions: List[ContradictionFinding],
        comparisons: List[PaperComparison],
        evidence_strength: EvidenceStrength,
        consensus_status: str,
        all_eids: List[str],
    ) -> ConsensusSynthesis:
        """
        Uses schema-constrained LLM to construct final consensus narrative
        derived strictly from Stage 4 intelligence artifacts.
        """
        findings_text = "\n".join(
            f"[{f.finding_id}] ({f.finding_type}): {f.finding_text} (Evidence: {f.evidence_ids})"
            for f in findings
        )
        divergences_text = "\n".join(
            f"- {ct.topic}: {'; '.join(ct.possible_explanations)}"
            for ct in contradictions
        ) or "None identified."

        prompt = f"""
You are a senior academic consensus rapporteur.
Synthesize the collective findings for research query: '{query}'

CRITICAL INSTRUCTIONS:
1. Synthesize ONLY what the provided structured findings state.
2. Evidence Strength Rating is: {evidence_strength.rating.value} ({evidence_strength.rationale}).
3. If evidence is LIMITED, explicitly qualify that findings reflect initial or single-study observations.
4. Highlight methodological nuances or divergent points where findings differ by dataset or setting.
5. cited_evidence_ids MUST only contain valid evidence IDs ([E001], etc.).

Structured Findings:
{findings_text}

Methodological Discrepancies:
{divergences_text}
"""
        response = generate_structured_output(
            prompt=prompt,
            schema=LLMConsensusOutput,
            system_instruction="You are a strict meta-analytic synthesis auditor.",
            max_retries=1,
        )

        valid_eids = [eid for eid in response.cited_evidence_ids if eid in all_eids]
        if not valid_eids:
            for f in findings:
                valid_eids.extend([e for e in f.evidence_ids if e in all_eids])
        if not valid_eids:
            valid_eids = all_eids[:4]

        return ConsensusSynthesis(
            consensus_status=consensus_status,
            synthesis_statement=response.synthesis_statement,
            divergent_points=response.divergent_points,
            evidence_strength=evidence_strength,
            supporting_evidence_ids=valid_eids,
        )

    def _heuristic_synthesize(
        self,
        query: str,
        findings: List[ResearchFinding],
        contradictions: List[ContradictionFinding],
        evidence_strength: EvidenceStrength,
        consensus_status: str,
        all_eids: List[str],
    ) -> ConsensusSynthesis:
        """
        Deterministic consensus synthesis for fallback.
        """
        finding_texts = [f.finding_text for f in findings]
        statement = " ".join(finding_texts) if finding_texts else (
            f"Retrieved literature for '{query}' indicates {consensus_status.lower()} findings "
            f"across {evidence_strength.supporting_paper_count} evaluated papers."
        )

        divergent_points = [
            f"{ct.topic}: {'; '.join(ct.possible_explanations)}"
            for ct in contradictions
        ]

        return ConsensusSynthesis(
            consensus_status=consensus_status,
            synthesis_statement=statement,
            divergent_points=divergent_points,
            evidence_strength=evidence_strength,
            supporting_evidence_ids=all_eids[:4],
        )
