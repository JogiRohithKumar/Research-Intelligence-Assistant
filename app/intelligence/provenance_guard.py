"""
Provenance Guard for Research Intelligence Assistant V2 (Stage 4).
Enforces non-negotiable provenance chain from Stage 4 intelligence objects
back to Stage 3 ResearchClaim and EvidenceChunk objects.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from app.core.logging import logger
from app.models.domain import (
    ClaimSupportStatus,
    ContradictionFinding,
    EvidenceChunk,
    PaperComparison,
    ResearchClaim,
    ResearchFinding,
    ResearchGapFinding,
)


class ProvenanceGuard:
    """
    Validates end-to-end evidence and claim provenance for Stage 4 intelligence.
    Ensures no intelligence finding is promoted into the final report unless
    every referenced claim ID, evidence ID, and paper ID genuinely exists
    and maps to underlying evidence excerpts.
    """

    def __init__(
        self,
        evidence_chunks: List[EvidenceChunk],
        claims: List[ResearchClaim],
        candidate_papers: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.evidence_by_id: Dict[str, EvidenceChunk] = {
            ev.evidence_id: ev for ev in evidence_chunks
        }
        self.claims_by_id: Dict[str, ResearchClaim] = {
            c.claim_id: c for c in claims
        }
        
        # Valid paper IDs from evidence chunks and candidate papers
        self.valid_paper_ids: Set[str] = {
            ev.paper_id for ev in evidence_chunks if ev.paper_id
        }
        if candidate_papers:
            for p in candidate_papers:
                pid = p.get("paper_id") or p.get("id")
                if pid:
                    self.valid_paper_ids.add(str(pid))

    def verify_finding(self, finding: ResearchFinding) -> Tuple[bool, str]:
        """
        Verifies that a ResearchFinding has valid provenance.
        Returns (is_valid, reason).
        """
        # 1. Evidence IDs must exist in the session evidence registry
        if not finding.evidence_ids:
            # Also check if it references claim_ids that themselves have evidence
            has_claim_evidence = False
            for cid in finding.claim_ids:
                claim = self.claims_by_id.get(cid)
                if claim and claim.evidence_ids:
                    # Propagate evidence IDs from claim
                    for eid in claim.evidence_ids:
                        if eid in self.evidence_by_id:
                            finding.evidence_ids.append(eid)
                            has_claim_evidence = True
            if not has_claim_evidence and not finding.evidence_ids:
                return False, f"Finding '{finding.finding_id}' cites zero valid evidence IDs."

        # Verify every cited evidence ID exists
        invalid_eids = [eid for eid in finding.evidence_ids if eid not in self.evidence_by_id]
        if invalid_eids:
            return False, f"Finding '{finding.finding_id}' references non-existent evidence IDs: {invalid_eids}"

        # 2. Check claim IDs if provided
        for cid in finding.claim_ids:
            if cid not in self.claims_by_id:
                return False, f"Finding '{finding.finding_id}' references non-existent claim ID: '{cid}'"

        # 3. Check paper IDs
        # Auto-populate or verify paper IDs from evidence chunks
        evidence_paper_ids = {
            self.evidence_by_id[eid].paper_id for eid in finding.evidence_ids if eid in self.evidence_by_id
        }
        if not finding.paper_ids:
            finding.paper_ids = sorted(list(evidence_paper_ids))
        else:
            for pid in finding.paper_ids:
                if pid not in self.valid_paper_ids and pid not in evidence_paper_ids:
                    return False, f"Finding '{finding.finding_id}' references unknown paper ID: '{pid}'"

        return True, "Provenance verified"

    def verify_comparison(self, comparison: PaperComparison) -> Tuple[bool, str]:
        """
        Verifies that a PaperComparison references a known paper and evidence.
        """
        if comparison.paper_id not in self.valid_paper_ids:
            return False, f"Comparison references unknown paper_id: '{comparison.paper_id}'"

        invalid_eids = [eid for eid in comparison.evidence_ids if eid not in self.evidence_by_id]
        if invalid_eids:
            return False, f"Comparison references non-existent evidence IDs: {invalid_eids}"

        return True, "Provenance verified"

    def verify_contradiction(self, contradiction: ContradictionFinding) -> Tuple[bool, str]:
        """
        Verifies that a ContradictionFinding connects real papers and real evidence.
        """
        if contradiction.paper_a_id not in self.valid_paper_ids:
            return False, f"Contradiction references unknown paper_a_id: '{contradiction.paper_a_id}'"
        if contradiction.paper_b_id not in self.valid_paper_ids:
            return False, f"Contradiction references unknown paper_b_id: '{contradiction.paper_b_id}'"

        if not contradiction.evidence_ids:
            return False, f"Contradiction '{contradiction.contradiction_id}' contains zero evidence references."

        invalid_eids = [eid for eid in contradiction.evidence_ids if eid not in self.evidence_by_id]
        if invalid_eids:
            return False, f"Contradiction references non-existent evidence IDs: {invalid_eids}"

        return True, "Provenance verified"

    def verify_gap(self, gap: ResearchGapFinding) -> Tuple[bool, str]:
        """
        Verifies that a ResearchGapFinding references valid affected papers or evidence.
        """
        if gap.supporting_evidence_ids:
            invalid_eids = [eid for eid in gap.supporting_evidence_ids if eid not in self.evidence_by_id]
            if invalid_eids:
                return False, f"Research gap references non-existent evidence IDs: {invalid_eids}"

        for pid in gap.affected_papers:
            if pid not in self.valid_paper_ids:
                return False, f"Research gap references unknown paper ID: '{pid}'"

        return True, "Provenance verified"

    def audit_and_filter_findings(
        self,
        findings: List[ResearchFinding],
        comparisons: List[PaperComparison],
        contradictions: List[ContradictionFinding],
        gaps: List[ResearchGapFinding],
    ) -> Dict[str, Any]:
        """
        Performs full audit across all Stage 4 objects, purging or flagging
        any items that fail provenance.
        """
        promoted_findings: List[ResearchFinding] = []
        rejected_findings: List[Dict[str, str]] = []

        for f in findings:
            valid, reason = self.verify_finding(f)
            if valid:
                promoted_findings.append(f)
            else:
                logger.warning(f"Provenance violation detected: {reason}")
                rejected_findings.append({"finding_id": f.finding_id, "reason": reason})

        promoted_comparisons: List[PaperComparison] = []
        for c in comparisons:
            valid, reason = self.verify_comparison(c)
            if valid:
                promoted_comparisons.append(c)
            else:
                logger.warning(f"Comparison provenance violation: {reason}")

        promoted_contradictions: List[ContradictionFinding] = []
        for ct in contradictions:
            valid, reason = self.verify_contradiction(ct)
            if valid:
                promoted_contradictions.append(ct)
            else:
                logger.warning(f"Contradiction provenance violation: {reason}")

        promoted_gaps: List[ResearchGapFinding] = []
        for g in gaps:
            valid, reason = self.verify_gap(g)
            if valid:
                promoted_gaps.append(g)
            else:
                logger.warning(f"Research gap provenance violation: {reason}")

        chain_intact = len(rejected_findings) == 0

        audit_summary = {
            "chain_intact": chain_intact,
            "total_findings": len(findings),
            "promoted_findings_count": len(promoted_findings),
            "rejected_findings_count": len(rejected_findings),
            "rejected_findings": rejected_findings,
            "total_comparisons": len(promoted_comparisons),
            "total_contradictions": len(promoted_contradictions),
            "total_gaps": len(promoted_gaps),
            "known_evidence_count": len(self.evidence_by_id),
            "known_claims_count": len(self.claims_by_id),
            "known_papers_count": len(self.valid_paper_ids),
        }

        logger.info(
            f"Provenance Audit completed: promoted={len(promoted_findings)}/{len(findings)} findings, "
            f"comparisons={len(promoted_comparisons)}, contradictions={len(promoted_contradictions)}, "
            f"gaps={len(promoted_gaps)}"
        )

        return {
            "findings": promoted_findings,
            "comparisons": promoted_comparisons,
            "contradictions": promoted_contradictions,
            "gaps": promoted_gaps,
            "audit_summary": audit_summary,
        }
