"""
Contradiction Detector for Research Intelligence Assistant V2 (Stage 4).
Distinguishes genuine substantive contradictions from differences in
datasets, populations, metrics, or experimental methodologies.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.models.domain import (
    ClaimSupportStatus,
    ContradictionFinding,
    ContradictionType,
    EvidenceChunk,
    PaperComparison,
    ResearchClaim,
)
from app.services.llm_service import generate_structured_output


class LLMContradictionItem(BaseModel):
    topic: str = Field(..., description="Common topic, method, or outcome being compared")
    paper_a_id: str
    paper_b_id: str
    claim_a: str
    claim_b: str
    cited_evidence_ids: List[str] = Field(default_factory=list)
    contradiction_type: ContradictionType = Field(default=ContradictionType.NOT_A_CONTRADICTION)
    is_genuine_contradiction: bool = Field(
        default=False,
        description="True ONLY if incompatible findings under the same condition. False if different datasets/methods explain it."
    )
    possible_explanations: List[str] = Field(
        default_factory=lambda: ["UNKNOWN"],
        description="Evidence-supported explanation for the difference; must be ['UNKNOWN'] if unverified"
    )


class LLMContradictionReport(BaseModel):
    contradictions: List[LLMContradictionItem] = Field(default_factory=list)


class ContradictionDetector:
    """
    Analyzes cross-paper claims and evidence to detect and classify
    substantive contradictions vs methodology/dataset differences.
    """

    def __init__(self, evidence_chunks: List[EvidenceChunk]) -> None:
        self.evidence_by_id = {c.evidence_id: c for c in evidence_chunks}

    def detect_contradictions(
        self,
        claims: List[ResearchClaim],
        comparisons: List[PaperComparison],
    ) -> List[ContradictionFinding]:
        """
        Main entrypoint: performs structured contradiction detection across papers.
        """
        # Collect papers with claims
        paper_ids = list({c.paper_id for c in self.evidence_by_id.values() if c.paper_id})
        if len(paper_ids) < 2 and len(claims) < 2:
            return []

        # First, attempt structured LLM analysis
        try:
            return self._llm_detect_contradictions(claims, comparisons)
        except Exception as e:
            logger.info(f"LLM contradiction analysis fallback: {e}")
            return self._heuristic_detect_contradictions(claims, comparisons)

    def _llm_detect_contradictions(
        self,
        claims: List[ResearchClaim],
        comparisons: List[PaperComparison],
    ) -> List[ContradictionFinding]:
        """
        Uses schema-constrained LLM to evaluate pairs of claims across papers.
        """
        claims_context = "\n".join(
            f"[{c.claim_id}] (Paper: {', '.join(c.source_paper_ids) or 'Unknown'}, Evidence: {c.evidence_ids}): {c.claim_text}"
            for c in claims
        )

        comparison_context = "\n".join(
            f"Paper: {c.paper_id} | Title: {c.paper_title} | Dataset: {c.dataset} | Method: {c.intervention_or_method} | Metrics: {c.metrics}"
            for c in comparisons
        )

        evidence_sample = "\n".join(
            f"[{c.evidence_id}] (Paper: {c.paper_id}): {c.text}"
            for c in list(self.evidence_by_id.values())[:15]
        )

        prompt = f"""
You are a senior scientific research auditor evaluating contradictions across research papers.

CRITICAL INSTRUCTIONS:
1. DO NOT CONFUSE DIFFERENCE WITH CONTRADICTION.
   - If Paper A evaluates Model X on Dataset 1, and Paper B evaluates Model Y on Dataset 2, different results are NOT a contradiction.
   - If outcomes differ because of differing populations, datasets, metrics, or baselines, classify as 'METHODOLOGY_DEPENDENT' or 'NOT_A_CONTRADICTION' and set is_genuine_contradiction=False.
2. ONLY classify as a genuine contradiction (is_genuine_contradiction=True) with 'DIRECT_RESULT_CONFLICT' or 'DIRECTIONAL_CONFLICT' when two papers evaluate the SAME condition, intervention, or proposition and reach incompatible findings (e.g., Paper A finds improvement while Paper B finds deterioration or no effect under comparable conditions).
3. Every explanation in possible_explanations MUST be grounded in the provided text. If the evidence does not provide a reason, you MUST return ["UNKNOWN"]. Never fabricate reasons.
4. cited_evidence_ids MUST only contain valid evidence IDs present in the text ([E001], etc.).

Papers & Methodologies:
{comparison_context}

Grounded Claims:
{claims_context}

Evidence Excerpts:
{evidence_sample}
"""
        response = generate_structured_output(
            prompt=prompt,
            schema=LLMContradictionReport,
            system_instruction="You are a strict academic contradiction verifier. Distinguish differences from contradictions.",
            max_retries=1,
        )

        findings: List[ContradictionFinding] = []
        for i, item in enumerate(response.contradictions, 1):
            # Verify evidence IDs
            valid_eids = [eid for eid in item.cited_evidence_ids if eid in self.evidence_by_id]
            if not valid_eids:
                # Find evidence IDs from claims if possible
                for c in claims:
                    if c.claim_text == item.claim_a or c.claim_text == item.claim_b:
                        valid_eids.extend([e for e in c.evidence_ids if e in self.evidence_by_id])
            if not valid_eids and list(self.evidence_by_id.keys()):
                valid_eids = list(self.evidence_by_id.keys())[:2]

            explanations = item.possible_explanations or ["UNKNOWN"]

            findings.append(
                ContradictionFinding(
                    contradiction_id=f"CT{i:03d}",
                    topic=item.topic,
                    paper_a_id=item.paper_a_id,
                    paper_b_id=item.paper_b_id,
                    claim_a=item.claim_a,
                    claim_b=item.claim_b,
                    evidence_ids=valid_eids,
                    contradiction_type=item.contradiction_type,
                    possible_explanations=explanations,
                    is_genuine_contradiction=item.is_genuine_contradiction,
                    support_status=ClaimSupportStatus.SUPPORTED,
                )
            )

        return findings

    def _heuristic_detect_contradictions(
        self,
        claims: List[ResearchClaim],
        comparisons: List[PaperComparison],
    ) -> List[ContradictionFinding]:
        """
        Deterministic contradiction analysis:
        Compares claim pairs for opposite polarity (improves vs degrades/fails)
        and checks if datasets/methods differ.
        """
        findings: List[ContradictionFinding] = []
        comparisons_by_paper = {c.paper_id: c for c in comparisons}

        # Polarity keywords
        positive_keywords = {"improve", "improves", "improved", "outperform", "outperformed", "increase", "increased", "increases", "higher", "superior", "enhances", "effective"}
        negative_keywords = {"no improvement", "fails", "failed", "degrade", "degraded", "decrease", "decreased", "decreases", "lower", "inferior", "ineffective", "no significant", "not associated", "no association", "no effect"}

        # Compare pairs of claims from different papers
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                # Ensure from distinct papers
                p1_ids = set(c1.source_paper_ids)
                p2_ids = set(c2.source_paper_ids)
                if not p1_ids or not p2_ids or p1_ids == p2_ids:
                    continue

                p1_id = next(iter(p1_ids))
                p2_id = next(iter(p2_ids))

                text1 = c1.claim_text.lower()
                text2 = c2.claim_text.lower()

                # Check polarities
                has_pos1 = any(kw in text1 for kw in positive_keywords)
                has_neg1 = any(kw in text1 for kw in negative_keywords)
                has_pos2 = any(kw in text2 for kw in positive_keywords)
                has_neg2 = any(kw in text2 for kw in negative_keywords)

                is_opposite_polarity = (has_pos1 and has_neg2) or (has_neg1 and has_pos2)

                # Check if datasets/methods differ between paper comparisons
                comp1 = comparisons_by_paper.get(p1_id)
                comp2 = comparisons_by_paper.get(p2_id)

                different_datasets = False
                different_methods = False
                if comp1 and comp2:
                    if comp1.dataset and comp2.dataset and comp1.dataset.lower() != comp2.dataset.lower():
                        different_datasets = True
                    if comp1.intervention_or_method and comp2.intervention_or_method and comp1.intervention_or_method.lower() != comp2.intervention_or_method.lower():
                        different_methods = True

                shared_eids = [eid for eid in (c1.evidence_ids + c2.evidence_ids) if eid in self.evidence_by_id]
                if not shared_eids:
                    shared_eids = list(self.evidence_by_id.keys())[:2]

                if is_opposite_polarity:
                    if different_datasets:
                        # NOT a genuine contradiction: dataset difference!
                        findings.append(
                            ContradictionFinding(
                                contradiction_id=f"CT{len(findings)+1:03d}",
                                topic="Discrepancy across datasets",
                                paper_a_id=p1_id,
                                paper_b_id=p2_id,
                                claim_a=c1.claim_text,
                                claim_b=c2.claim_text,
                                evidence_ids=shared_eids,
                                contradiction_type=ContradictionType.METHODOLOGY_DEPENDENT,
                                possible_explanations=[
                                    f"Studies evaluated on different datasets: '{comp1.dataset}' vs '{comp2.dataset}'"
                                ],
                                is_genuine_contradiction=False,
                                support_status=ClaimSupportStatus.SUPPORTED,
                            )
                        )
                    elif different_methods:
                        findings.append(
                            ContradictionFinding(
                                contradiction_id=f"CT{len(findings)+1:03d}",
                                topic="Methodology-dependent outcome",
                                paper_a_id=p1_id,
                                paper_b_id=p2_id,
                                claim_a=c1.claim_text,
                                claim_b=c2.claim_text,
                                evidence_ids=shared_eids,
                                contradiction_type=ContradictionType.METHODOLOGY_DEPENDENT,
                                possible_explanations=[
                                    f"Different evaluated methods: '{comp1.intervention_or_method}' vs '{comp2.intervention_or_method}'"
                                ],
                                is_genuine_contradiction=False,
                                support_status=ClaimSupportStatus.SUPPORTED,
                            )
                        )
                    else:
                        # Genuine directional or direct contradiction
                        findings.append(
                            ContradictionFinding(
                                contradiction_id=f"CT{len(findings)+1:03d}",
                                topic="Direct outcome conflict under comparable settings",
                                paper_a_id=p1_id,
                                paper_b_id=p2_id,
                                claim_a=c1.claim_text,
                                claim_b=c2.claim_text,
                                evidence_ids=shared_eids,
                                contradiction_type=ContradictionType.DIRECT_RESULT_CONFLICT,
                                possible_explanations=["UNKNOWN"],
                                is_genuine_contradiction=True,
                                support_status=ClaimSupportStatus.SUPPORTED,
                            )
                        )

        return findings
