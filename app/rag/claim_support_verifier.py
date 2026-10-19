"""
Semantic Claim-to-Evidence Support Verifier for Research Intelligence Assistant V2 (Stage 3).
Evaluates whether referenced evidence text actually entails and substantiates research claims.
Distinguishes SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, and INSUFFICIENT_EVIDENCE.
"""

import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.models.domain import (
    EvidenceChunk,
    EvidenceSupportResult,
    ResearchClaim,
    SupportVerdict,
)
from app.services.llm_service import generate_structured_output

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "show", "showed", "shows", "demonstrate", "demonstrated",
    "demonstrates", "report", "reported", "reports", "found", "finds", "finding", "findings"
}

SUPERLATIVE_PATTERNS: List[str] = [
    r"\boutperformed\s+all\b",
    r"\bsuperior\s+to\s+(?:all|every)\b",
    r"\bbest\s+(?:in|among|overall)\b",
    r"\bevery\s+competing\b",
    r"\ball\s+competing\b",
    r"\buniversally\b",
    r"\bsurpassed\s+all\b",
    r"\bin\s+all\s+cases\b",
    r"\balways\s+outperforms\b",
]

CAUSAL_PATTERNS: List[str] = [
    r"\bbecause\s+it\s+",
    r"\bcauses\s+",
    r"\bcaused\s+by\s+",
    r"\bdue\s+to\s+the\s+fact\s+that\b",
    r"\bas\s+a\s+result\s+of\b",
    r"\bthereby\s+causing\b",
    r"\bmechanism\s+of\b",
]


class LLMSupportVerificationOutput(BaseModel):
    verdict: SupportVerdict
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    explanation: str = Field(default="", description="Strict factual explanation relying exclusively on evidence")


class ClaimSupportVerifier:
    """
    Dedicated semantic verification engine for research claims against retrieved evidence.
    Ensures claims are substantiated by evidence content rather than just referencing valid IDs.
    """

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm

    def _normalize_token(self, token: str) -> str:
        """Strip common morphological inflections for robust semantic matching."""
        t = token.lower().strip("%")
        for suffix in ("ations", "ation", "ating", "ting", "tions", "tion", "ments", "ment", "ing", "ies", "ied", "ed", "ors", "ers", "or", "er", "es", "s", "ive", "acy", "cy", "al", "ly"):
            if t.endswith(suffix) and len(t) - len(suffix) >= 3:
                t = t[:-len(suffix)]
                break
        if t in {"effic", "effect"}:
            return "effic"
        return t

    def _token_coverage(self, claim_text: str, evidence_text: str) -> float:
        """Calculates normalized content token coverage of claim in evidence."""
        raw_claim_words = [w for w in re.findall(r"\b[a-zA-Z0-9_%-]{3,}\b", claim_text.lower()) if w not in STOPWORDS]
        if not raw_claim_words:
            return 0.0

        evidence_words = set(re.findall(r"\b[a-zA-Z0-9_%-]{3,}\b", evidence_text.lower()))
        evidence_stems = {self._normalize_token(w) for w in evidence_words}

        matches = 0
        for w in raw_claim_words:
            stem = self._normalize_token(w)
            if w in evidence_words or stem in evidence_stems:
                matches += 1

        return matches / len(raw_claim_words)

    def verify_support(
        self,
        claim: ResearchClaim,
        evidence_chunks: List[EvidenceChunk]
    ) -> EvidenceSupportResult:
        """
        Evaluates whether the given evidence chunks factually support the research claim.
        Receives ONLY the claim, relevant evidence text, and source metadata.
        """
        # 1. Immediate insufficiency check
        if not evidence_chunks:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=[],
                explanation="No evidence chunks provided to substantiate this claim."
            )

        valid_chunks = [c for c in evidence_chunks if c and c.text.strip()]
        if not valid_chunks:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.INSUFFICIENT_EVIDENCE,
                supporting_evidence_ids=[],
                explanation="Provided evidence chunks contain no substantive text."
            )

        # 2. Attempt structured LLM verification if explicitly requested
        if self.use_llm:
            llm_result = self._try_llm_verify(claim, valid_chunks)
            if llm_result is not None:
                return llm_result

        # 3. High-precision deterministic semantic verification
        return self._deterministic_semantic_verify(claim, valid_chunks)

    def _try_llm_verify(
        self,
        claim: ResearchClaim,
        evidence_chunks: List[EvidenceChunk]
    ) -> Optional[EvidenceSupportResult]:
        """Runs structured schema-constrained peer-review prompt via LLM."""
        evidence_blocks = []
        for c in evidence_chunks:
            authors_str = ", ".join(c.authors[:3]) if c.authors else "Unknown Authors"
            year_str = str(c.year) if c.year else "N/A"
            evidence_blocks.append(
                f"[{c.evidence_id}]\n"
                f"Paper: {c.title} ({authors_str}, {year_str})\n"
                f"Excerpt: \"{c.text}\""
            )
        formatted_evidence = "\n\n".join(evidence_blocks)

        prompt = f"""You are a strict, objective scientific peer-review referee.
Your SOLE task is to verify whether the provided EVIDENCE TEXT factually supports the RESEARCH CLAIM.

RESEARCH CLAIM:
"{claim.claim_text}"

CITED EVIDENCE:
{formatted_evidence}

VERIFICATION RULES:
1. Base your verdict EXCLUSIVELY on the provided evidence text. Do NOT use external knowledge.
2. "SUPPORTED": The evidence directly and fully supports all factual propositions and figures in the claim.
3. "PARTIALLY_SUPPORTED": The evidence supports part of the claim, but the claim asserts extra unverified claims, superlatives (e.g. "outperformed all"), or unproven causal mechanisms (e.g. "because it reduces bias") not present in the evidence.
4. "UNSUPPORTED": The evidence is irrelevant, discusses a different topic, fails to substantiate the claim, or the metrics/facts do not match.
5. "INSUFFICIENT_EVIDENCE": The evidence text is inadequate or missing to make a factual determination.
"""
        try:
            output = generate_structured_output(
                prompt=prompt,
                schema=LLMSupportVerificationOutput,
                system_instruction="You are a strict scientific grounding verifier. Never invent facts or grant unwarranted support."
            )
            if output and output.verdict:
                return EvidenceSupportResult(
                    claim_id=claim.claim_id,
                    verdict=output.verdict,
                    supporting_evidence_ids=output.supporting_evidence_ids or [c.evidence_id for c in evidence_chunks],
                    explanation=output.explanation
                )
        except Exception as e:
            logger.debug(f"LLM semantic verification skipped ({e}); executing deterministic semantic verifier")

        return None

    def _deterministic_semantic_verify(
        self,
        claim: ResearchClaim,
        evidence_chunks: List[EvidenceChunk]
    ) -> EvidenceSupportResult:
        """
        High-precision deterministic semantic support verification.
        Analyzes lexical entailment, quantitative metrics, scope expansion, and causal mechanism assertions.
        """
        claim_text = claim.claim_text.strip()
        claim_lower = claim_text.lower()
        chunk_eids = [c.evidence_id for c in evidence_chunks]

        combined_evidence = " ".join(f"{c.title} {c.section or ''} {c.text}" for c in evidence_chunks)
        evidence_lower = combined_evidence.lower()

        # A. Check for explicit cross-paper reference mismatch
        # e.g. Claim mentions "Paper A" or "Study A" but evidence is from Paper B
        paper_matches = re.findall(r"\b(?:paper|study)\s+([a-zA-Z0-9]+)\b", claim_lower)
        if paper_matches:
            for pm in paper_matches:
                tag = f"paper {pm}"
                study_tag = f"study {pm}"
                matches_any = any(
                    tag in c.title.lower() or tag in c.paper_id.lower() or
                    study_tag in c.title.lower() or study_tag in c.paper_id.lower() or
                    (len(pm) > 1 and (pm in c.title.lower() or pm in c.paper_id.lower()))
                    for c in evidence_chunks
                )
                if not matches_any:
                    return EvidenceSupportResult(
                        claim_id=claim.claim_id,
                        verdict=SupportVerdict.UNSUPPORTED,
                        supporting_evidence_ids=[],
                        explanation=f"Claim asserts findings about Study/Paper '{pm.upper()}', but cited evidence originates from unrelated sources."
                    )

        # B. Check for explicit literature absence of clinical trials or empirical evidence
        absence_markers = [
            "no phase 3", "no clinical trials", "have not been completed",
            "have not been performed", "remains unstudied", "no evidence of"
        ]
        if any(marker in evidence_lower for marker in absence_markers):
            if any(term in claim_lower for term in ["phase 3", "clinical trial", "cure", "survival benefit", "proven", "insufficient"]):
                return EvidenceSupportResult(
                    claim_id=claim.claim_id,
                    verdict=SupportVerdict.INSUFFICIENT_EVIDENCE,
                    supporting_evidence_ids=chunk_eids,
                    explanation="Retrieved literature explicitly reports absence of completed clinical trial data."
                )

        # C. Check for quantitative metric hallucination
        claim_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", claim_text))
        evidence_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", combined_evidence))

        # Filter out trivial numbers
        missing_numbers = {n for n in (claim_numbers - evidence_numbers) if n not in {"1", "2", "3", "001", "002"}}

        coverage = self._token_coverage(claim_text, combined_evidence)

        # If claim contains quantitative metrics that do not exist in the evidence -> UNSUPPORTED
        if missing_numbers:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.UNSUPPORTED,
                supporting_evidence_ids=[],
                explanation=f"Evidence does not support quantitative claim; missing metric(s): {sorted(list(missing_numbers))}."
            )

        # If token coverage is below minimum relevance threshold (< 40% non-stopword stem match)
        if coverage < 0.40:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.UNSUPPORTED,
                supporting_evidence_ids=[],
                explanation=f"Evidence text is irrelevant to claim concepts (content coverage {coverage:.1%})."
            )

        # D. Check for unsubstantiated superlatives / extreme scope
        # e.g. "Treatment A improved outcome B and outperformed all competing treatments."
        has_unsubstantiated_superlative = False
        for pat in SUPERLATIVE_PATTERNS:
            if re.search(pat, claim_lower) and not re.search(pat, evidence_lower):
                has_unsubstantiated_superlative = True
                break

        if has_unsubstantiated_superlative:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.PARTIALLY_SUPPORTED,
                supporting_evidence_ids=chunk_eids,
                explanation="Evidence substantiates baseline finding, but fails to substantiate superlative or absolute superiority claim."
            )

        # E. Check for unsubstantiated causal mechanisms
        # e.g. "Method A causes higher accuracy because it reduces model bias."
        has_unsubstantiated_cause = False
        for pat in CAUSAL_PATTERNS:
            cause_match = re.search(pat, claim_lower)
            if cause_match and not re.search(pat, evidence_lower):
                after_cause = claim_lower[cause_match.end():].split(".")[0].strip()
                cause_coverage = self._token_coverage(after_cause, combined_evidence)
                if cause_coverage < 0.50:
                    has_unsubstantiated_cause = True
                    break

        if has_unsubstantiated_cause:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.PARTIALLY_SUPPORTED,
                supporting_evidence_ids=chunk_eids,
                explanation="Evidence supports observed outcome, but does not substantiate the asserted causal mechanism."
            )

        # F. Direct Support vs Partial Support evaluation
        if coverage >= 0.55:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.SUPPORTED,
                supporting_evidence_ids=chunk_eids,
                explanation=f"Evidence directly substantiates factual claim propositions and metrics ({coverage:.1%} content alignment)."
            )
        else:
            return EvidenceSupportResult(
                claim_id=claim.claim_id,
                verdict=SupportVerdict.PARTIALLY_SUPPORTED,
                supporting_evidence_ids=chunk_eids,
                explanation=f"Evidence partially supports claim ({coverage:.1%} alignment), but some assertions lack explicit evidence."
            )

    verify_claim_support = verify_support


EvidenceSupportVerifier = ClaimSupportVerifier

def verify_claim_support(claim: ResearchClaim, evidence_chunks: List[EvidenceChunk]) -> EvidenceSupportResult:
    """Module-level convenience wrapper for ClaimSupportVerifier."""
    return ClaimSupportVerifier().verify_support(claim, evidence_chunks)
