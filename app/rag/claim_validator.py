"""
Claim-to-Evidence Validator and Citation Verifier for Research Intelligence Assistant V2 (Stage 3).
Enforces machine-readable claim grounding, quote integrity verification, and unsupported claim detection.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.core.logging import logger
from app.models.domain import (
    ClaimSupportStatus,
    CitationVerificationResult,
    EvidenceChunk,
    ResearchClaim,
)
from app.rag.claim_support_verifier import ClaimSupportVerifier
from app.rag.evidence import EvidenceRegistry


class ClaimEvidenceValidator:
    """
    Validates that factual claims deterministically map to real, session-registered EvidenceChunks
    AND that referenced evidence text actually provides semantic support for the claim.
    Prevents unsupported claims from becoming grounded research findings.
    """

    def __init__(self, support_verifier: Optional[ClaimSupportVerifier] = None):
        self.support_verifier = support_verifier or ClaimSupportVerifier()

    def validate_claim(
        self,
        claim: ResearchClaim,
        registry: EvidenceRegistry
    ) -> ResearchClaim:
        """
        Validates a single ResearchClaim against the active EvidenceRegistry.
        1. Validates that evidence IDs exist in claim.
        2. Validates that referenced evidence IDs exist in registry.
        3. Executes Semantic Support Verification to ensure evidence actually substantiates the claim.
        4. Mutates claim in-place and returns it.
        """
        # 1. Check for empty evidence references
        if not claim.evidence_ids:
            claim.support_status = ClaimSupportStatus.UNSUPPORTED
            claim.confidence_rationale = "Rejected: No evidence IDs referenced for factual claim."
            claim.source_paper_ids = []
            return claim

        # 2. Check for existence in registry
        missing_ids = [eid for eid in claim.evidence_ids if not registry.has(eid)]
        valid_ids = [eid for eid in claim.evidence_ids if registry.has(eid)]

        if missing_ids:
            claim.support_status = ClaimSupportStatus.UNSUPPORTED
            claim.confidence_rationale = f"Rejected: Referenced invalid/unknown evidence ID(s): {missing_ids}"
            claim.source_paper_ids = []
            return claim

        # 3. Resolve true source paper IDs and chunks from verified evidence
        resolved_paper_ids: Set[str] = set()
        evidence_chunks: List[EvidenceChunk] = []
        for eid in valid_ids:
            chunk = registry.get(eid)
            if chunk:
                evidence_chunks.append(chunk)
                if chunk.paper_id:
                    resolved_paper_ids.add(chunk.paper_id)

        claim.source_paper_ids = sorted(list(resolved_paper_ids))

        # 4. Critical Stage 3 Semantic Support Verification
        # Valid ID alone is NOT sufficient. Evidence text must factually support the claim.
        support_result = self.support_verifier.verify_support(claim, evidence_chunks)

        claim.support_status = ClaimSupportStatus(support_result.verdict)
        claim.confidence_rationale = support_result.explanation

        # If unsupported, clear ungrounded claims' source paper references
        if claim.support_status == ClaimSupportStatus.UNSUPPORTED:
            claim.evidence_ids = []
            claim.source_paper_ids = []

        return claim

    def validate_claims(
        self,
        claims: List[ResearchClaim],
        registry: EvidenceRegistry
    ) -> Tuple[List[ResearchClaim], List[ResearchClaim]]:
        """
        Validates a list of claims.
        Returns a tuple of (supported_claims, unsupported_claims).
        """
        supported: List[ResearchClaim] = []
        unsupported: List[ResearchClaim] = []

        for c in claims:
            validated = self.validate_claim(c, registry)
            if validated.support_status == ClaimSupportStatus.SUPPORTED:
                supported.append(validated)
            else:
                unsupported.append(validated)

        logger.info(
            f"ClaimEvidenceValidator: {len(supported)} claims validated as SUPPORTED, "
            f"{len(unsupported)} flagged as UNSUPPORTED"
        )
        return supported, unsupported


class CitationVerifier:
    """
    Performs comprehensive citation validation and quote integrity verification.
    """

    def _extract_quoted_passages(self, text: str) -> List[str]:
        """Extracts direct quotes delimited by quotation marks."""
        # Find text inside double quotes with length > 15 characters
        matches = re.findall(r'"([^"\n]{15,})"', text)
        return [m.strip() for m in matches if len(m.strip()) >= 15]

    def verify_quote_integrity(
        self,
        claim: ResearchClaim,
        registry: EvidenceRegistry
    ) -> List[Dict[str, str]]:
        """
        Checks that any exact quotes in claim_text or exact_quotes
        actually appear verbatim in the referenced evidence chunks.
        """
        failures: List[Dict[str, str]] = []
        quotes_to_check = set(claim.exact_quotes)

        # Also extract quotes from the claim text itself
        for q in self._extract_quoted_passages(claim.claim_text):
            quotes_to_check.add(q)

        if not quotes_to_check:
            return []

        # Gather combined text of all referenced evidence chunks
        evidence_texts = [
            registry.get(eid).text.lower()
            for eid in claim.evidence_ids
            if registry.has(eid) and registry.get(eid) is not None
        ]
        combined_evidence = " ".join(evidence_texts)

        for quote in quotes_to_check:
            # Normalize whitespace for substring search
            norm_quote = re.sub(r"\s+", " ", quote).lower()
            norm_evidence = re.sub(r"\s+", " ", combined_evidence)

            if norm_quote not in norm_evidence:
                failures.append({
                    "claim_id": claim.claim_id,
                    "quote": quote,
                    "reason": "Quoted passage does not exist in referenced evidence chunks."
                })

        return failures

    def verify_all(
        self,
        claims: List[ResearchClaim],
        registry: EvidenceRegistry
    ) -> CitationVerificationResult:
        """
        Executes full citation and quote integrity verification across all claims.
        """
        validator = ClaimEvidenceValidator()
        for c in claims:
            validator.validate_claim(c, registry)

        all_quote_failures: List[Dict[str, str]] = []
        total_citations = sum(len(c.evidence_ids) for c in claims)
        valid_citations = sum(
            len([eid for eid in c.evidence_ids if registry.has(eid)])
            for c in claims
        )
        invalid_citations = total_citations - valid_citations

        # Verify quote integrity across all claims
        for claim in claims:
            quote_fails = self.verify_quote_integrity(claim, registry)
            if quote_fails:
                all_quote_failures.extend(quote_fails)
                claim.support_status = ClaimSupportStatus.PARTIALLY_SUPPORTED
                if "unverified or paraphrased quotation" not in claim.confidence_rationale:
                    claim.confidence_rationale += " Caveat: Contains unverified or paraphrased quotation."

        supported = [c for c in claims if c.support_status == ClaimSupportStatus.SUPPORTED]
        unsupported = [c for c in claims if c.support_status == ClaimSupportStatus.UNSUPPORTED]
        partially_supported = [c for c in claims if c.support_status == ClaimSupportStatus.PARTIALLY_SUPPORTED]
        unsupported_ids = [c.claim_id for c in unsupported]

        # Determine overall grounding status
        if not claims or (len(unsupported) == len(claims) and len(claims) > 0):
            grounding_status = "UNGROUNDED"
        elif unsupported or partially_supported or all_quote_failures:
            grounding_status = "PARTIAL"
        else:
            grounding_status = "VERIFIED"

        result = CitationVerificationResult(
            total_claims=len(claims),
            supported_claims=len(supported),
            partially_supported_claims=len(partially_supported),
            unsupported_claims=len(unsupported),
            total_citations=total_citations,
            valid_citations=valid_citations,
            invalid_citations=invalid_citations,
            quote_integrity_failures=all_quote_failures,
            unsupported_claim_ids=unsupported_ids,
            grounding_status=grounding_status,
            notes=[
                f"Grounding status: {grounding_status}",
                f"{len(supported)}/{len(claims)} claims fully verified with source evidence ({len(partially_supported)} partially supported).",
            ]
        )

        return result
