"""
Actionable Gap Analyzer for Stage 5 Agentic Research Loop.
Extracts, prioritizes, and grounds actionable gaps across Stage 3 claims,
Stage 4 findings, contradictions, and evidence coverage patterns.
"""

from typing import Any, Dict, List
import uuid
from app.core.logging import logger
from app.models.domain import (
    ActionableResearchGap,
    ResearchGapCategory,
)


class ActionableGapAnalyzer:
    """
    Identifies concrete, actionable research gaps from current evidence state.
    Every gap is grounded in specific claim IDs, evidence IDs, or paper IDs.
    """

    def analyze(
        self,
        query: str,
        papers: List[Dict[str, Any]],
        evidence_registry: List[Dict[str, Any]],
        claims: List[Dict[str, Any]],
        intelligence: Dict[str, Any],
    ) -> List[ActionableResearchGap]:
        """
        Synthesizes and prioritizes actionable gaps that can be targeted in subsequent iterations.
        """
        actionable_gaps: List[ActionableResearchGap] = []
        seen_descriptions = set()

        # 1. Gaps from genuine contradictions in literature
        contradictions = intelligence.get("contradictions", [])
        for c in contradictions:
            if c.get("is_genuine_contradiction") or str(c.get("contradiction_type", "")).upper() == "DIRECT_RESULT_CONFLICT":
                topic = c.get("topic", "divergent findings")
                claim_a = c.get("claim_a", "")
                claim_b = c.get("claim_b", "")
                desc = (
                    f"Direct empirical contradiction detected regarding '{topic}': "
                    f"'{claim_a[:80]}' vs '{claim_b[:80]}'."
                )
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    actionable_gaps.append(
                        ActionableResearchGap(
                            gap_id=f"GAP_CONTRADICTION_{uuid.uuid4().hex[:6]}",
                            title=f"Contradiction: {topic[:50]}",
                            description=desc,
                            category="CONTRADICTION",
                            severity="HIGH",
                            evidence_ids=c.get("evidence_ids", []),
                            affected_papers=[c.get("paper_a_id", ""), c.get("paper_b_id", "")],
                            recommended_research_action=(
                                f"Conduct targeted comparison search evaluating methodological or cohort "
                                f"differences between {c.get('paper_a_id', 'Paper A')} and {c.get('paper_b_id', 'Paper B')}."
                            )
                        )
                    )

        # 2. Gaps from unsupported claims in grounded synthesis
        for c in claims:
            status = str(c.get("support_status", "UNSUPPORTED")).upper()
            if status in ("UNSUPPORTED", "INSUFFICIENT_EVIDENCE"):
                claim_text = c.get("claim_text", "")
                desc = f"Hypothesized proposition lacks empirical evidence in retrieved literature: '{claim_text}'"
                if desc not in seen_descriptions:
                    seen_descriptions.add(desc)
                    actionable_gaps.append(
                        ActionableResearchGap(
                            gap_id=f"GAP_UNSUPPORTED_{c.get('claim_id', uuid.uuid4().hex[:6])}",
                            title=f"Unverified Claim: {c.get('claim_id', 'C001')}",
                            description=desc,
                            category="UNSUPPORTED_CLAIM",
                            severity="HIGH",
                            evidence_ids=c.get("evidence_ids", []),
                            affected_papers=c.get("source_paper_ids", []),
                            recommended_research_action=f"Search specifically for empirical studies testing: '{claim_text[:100]}'."
                        )
                    )

        # 3. Gaps from Stage 4 Research Gap Findings
        stage4_gaps = intelligence.get("gaps", [])
        for g in stage4_gaps:
            g_desc = g.get("description", "")
            if g_desc and g_desc not in seen_descriptions:
                seen_descriptions.add(g_desc)
                cat = str(g.get("category", "EVIDENCE_GAP")).upper()
                sev = "HIGH" if cat in ("POPULATION_GAP", "DATASET_GAP") else "MEDIUM"
                actionable_gaps.append(
                    ActionableResearchGap(
                        gap_id=g.get("gap_id") or f"GAP_STAGE4_{uuid.uuid4().hex[:6]}",
                        title=f"Stage 4 Gap: {cat}",
                        description=g_desc,
                        category=cat,
                        severity=sev,
                        evidence_ids=g.get("supporting_evidence_ids", []),
                        affected_papers=g.get("affected_papers", []),
                        recommended_research_action=f"Retrieve studies addressing the identified {cat.lower()}: '{g_desc[:100]}'."
                    )
                )

        # 4. Single-Study Literature Concentration Gap
        unique_papers = {chunk.get("paper_id") for chunk in evidence_registry if chunk.get("paper_id")}
        if len(unique_papers) <= 1 and len(papers) >= 1:
            desc = "Within the retrieved literature, all verified evidence originates from a single study; independent replication or contrasting cohorts are absent."
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                actionable_gaps.append(
                    ActionableResearchGap(
                        gap_id=f"GAP_CONCENTRATION_{uuid.uuid4().hex[:6]}",
                        title="Single-Study Evidence Concentration",
                        description=desc,
                        category="GENERALIZATION_GAP",
                        severity="HIGH",
                        evidence_ids=[c.get("evidence_id") for c in evidence_registry[:2]],
                        affected_papers=list(unique_papers),
                        recommended_research_action=f"Search for independent evaluations and replication studies on '{query[:60]}'."
                    )
                )

        logger.info(f"[Stage 5 GapAnalyzer] Identified {len(actionable_gaps)} actionable gaps across claims and findings")
        return actionable_gaps
