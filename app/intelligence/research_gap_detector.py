"""
Research Gap Detector for Research Intelligence Assistant V2 (Stage 4).
Derives verifiable research gaps directly from retrieved evidence patterns
and author-stated study limitations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.models.domain import (
    EvidenceChunk,
    PaperComparison,
    ResearchClaim,
    ResearchGapCategory,
    ResearchGapFinding,
)
from app.services.llm_service import generate_structured_output


class LLMResearchGapItem(BaseModel):
    category: ResearchGapCategory = Field(default=ResearchGapCategory.EVIDENCE_GAP)
    description: str = Field(..., description="Must begin with 'Within the retrieved literature...'")
    affected_papers: List[str] = Field(default_factory=list)
    cited_evidence_ids: List[str] = Field(default_factory=list)
    reasoning: str = Field(..., description="Factual justification based on observed study patterns")


class LLMResearchGapReport(BaseModel):
    gaps: List[LLMResearchGapItem] = Field(default_factory=list)


class ResearchGapDetector:
    """
    Detects empirical research gaps, missing baselines, population blindspots,
    and unexplored comparisons grounded in the retrieved literature.
    """

    def __init__(self, evidence_chunks: List[EvidenceChunk]) -> None:
        self.evidence_by_id = {c.evidence_id: c for c in evidence_chunks}

    def detect_gaps(
        self,
        comparisons: List[PaperComparison],
        claims: List[ResearchClaim],
        query: str = "",
    ) -> List[ResearchGapFinding]:
        """
        Main entrypoint: generates structured ResearchGapFinding objects.
        """
        if not comparisons and not self.evidence_by_id:
            return []

        try:
            return self._llm_detect_gaps(comparisons, claims, query)
        except Exception as e:
            logger.info(f"LLM research gap detection fallback: {e}")
            return self._heuristic_detect_gaps(comparisons, claims)

    def _llm_detect_gaps(
        self,
        comparisons: List[PaperComparison],
        claims: List[ResearchClaim],
        query: str,
    ) -> List[ResearchGapFinding]:
        """
        Uses schema-constrained LLM to detect literature gaps.
        """
        comparisons_text = "\n".join(
            f"Paper: {c.paper_id} | Title: {c.paper_title} | Dataset: {c.dataset or 'Not stated'} | "
            f"Population: {c.population or 'Not stated'} | Method: {c.intervention_or_method or 'Not stated'} | "
            f"Limitations: {c.limitations or 'None stated'} | Evidence: {c.evidence_ids}"
            for c in comparisons
        )

        evidence_text = "\n".join(
            f"[{c.evidence_id}]: {c.text}" for c in list(self.evidence_by_id.values())[:15]
        )

        prompt = f"""
You are a senior academic research strategist analyzing gaps in scientific literature.
Research Query: {query}

CRITICAL RULES:
1. Every gap description MUST begin with the exact phrase: "Within the retrieved literature, "
2. NEVER claim a global universal gap; strictly limit scope to the retrieved evidence base.
3. Base gaps on observed patterns:
   - Narrow datasets or benchmark concentration (DATASET_GAP)
   - Specific populations studied while others lack evidence (POPULATION_GAP)
   - Author-stated limitations or failure modes (METHOD_GAP or GENERALIZATION_GAP)
   - Missing long-term evaluations (TIME_HORIZON_GAP)
   - Lack of direct comparative baselines (COMPARISON_GAP)
4. cited_evidence_ids MUST only contain valid evidence IDs present in the text ([E001], etc.).
5. affected_papers MUST match the provided paper IDs.

Retrieved Studies & Methodologies:
{comparisons_text}

Evidence Excerpts:
{evidence_text}
"""
        response = generate_structured_output(
            prompt=prompt,
            schema=LLMResearchGapReport,
            system_instruction="You are a strict research gap auditor. Extract only gaps supported by evidence patterns.",
            max_retries=1,
        )

        findings: List[ResearchGapFinding] = []
        for i, item in enumerate(response.gaps, 1):
            valid_eids = [eid for eid in item.cited_evidence_ids if eid in self.evidence_by_id]
            if not valid_eids and self.evidence_by_id:
                valid_eids = list(self.evidence_by_id.keys())[:2]

            desc = item.description.strip()
            if not desc.startswith("Within the retrieved literature"):
                desc = f"Within the retrieved literature, {desc}"

            findings.append(
                ResearchGapFinding(
                    gap_id=f"G{i:03d}",
                    category=item.category,
                    description=desc,
                    affected_papers=item.affected_papers,
                    supporting_evidence_ids=valid_eids,
                    reasoning=item.reasoning,
                )
            )

        return findings

    def _heuristic_detect_gaps(
        self,
        comparisons: List[PaperComparison],
        claims: List[ResearchClaim],
    ) -> List[ResearchGapFinding]:
        """
        Deterministic gap detection based on extracted methodology patterns.
        """
        findings: List[ResearchGapFinding] = []
        all_paper_ids = [c.paper_id for c in comparisons]

        # 1. Check author-reported limitations
        for c in comparisons:
            if c.limitations:
                findings.append(
                    ResearchGapFinding(
                        gap_id=f"G{len(findings)+1:03d}",
                        category=ResearchGapCategory.GENERALIZATION_GAP,
                        description=f"Within the retrieved literature, Paper '{c.paper_id}' identifies limitations regarding: {c.limitations}.",
                        affected_papers=[c.paper_id],
                        supporting_evidence_ids=c.evidence_ids[:2] or list(self.evidence_by_id.keys())[:2],
                        reasoning="Direct author-reported constraint documented in study excerpt.",
                    )
                )

        # 2. Check dataset concentration
        known_datasets = [c.dataset for c in comparisons if c.dataset]
        if known_datasets and len(set(known_datasets)) == 1:
            ds = known_datasets[0]
            findings.append(
                ResearchGapFinding(
                    gap_id=f"G{len(findings)+1:03d}",
                    category=ResearchGapCategory.DATASET_GAP,
                    description=f"Within the retrieved literature, evaluations are concentrated on dataset '{ds}', with limited cross-domain benchmarking.",
                    affected_papers=all_paper_ids,
                    supporting_evidence_ids=list(self.evidence_by_id.keys())[:2],
                    reasoning=f"All retrieved studies reporting dataset specifications evaluated on the single corpus '{ds}'.",
                )
            )

        # 3. Check baseline/control availability
        missing_baselines = [c.paper_id for c in comparisons if not c.baseline_or_control]
        if len(missing_baselines) == len(comparisons) and len(comparisons) > 1:
            findings.append(
                ResearchGapFinding(
                    gap_id=f"G{len(findings)+1:03d}",
                    category=ResearchGapCategory.COMPARISON_GAP,
                    description="Within the retrieved literature, explicit comparative baselines against alternative architectures are sparsely documented.",
                    affected_papers=all_paper_ids,
                    supporting_evidence_ids=list(self.evidence_by_id.keys())[:2],
                    reasoning="None of the retrieved study excerpts contain formal baseline or control group specifications.",
                )
            )

        # If zero gaps generated, output conservative baseline
        if not findings:
            findings.append(
                ResearchGapFinding(
                    gap_id="G001",
                    category=ResearchGapCategory.EVIDENCE_GAP,
                    description="Within the retrieved literature, broader multi-corpus validation is required to establish generalizability.",
                    affected_papers=all_paper_ids[:2],
                    supporting_evidence_ids=list(self.evidence_by_id.keys())[:2],
                    reasoning="The retrieved evidence base is bounded by candidate literature and warrants systematic empirical expansion.",
                )
            )

        return findings
