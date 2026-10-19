"""
Claim & Citation Alignment Metrics.
Evaluates citation validity, claim grounding accuracy, causal overreach detection,
and superlative claim hygiene.
"""

import re
from typing import Any, Dict, List, Set

CAUSAL_INDICATORS = [
    r"\bcauses\b", r"\bcaused\b", r"\bcausing\b",
    r"\bproves\b", r"\bproven\b",
    r"\bprevents\b", r"\bcures\b",
    r"\bdirectly leads to\b", r"\bdetermines\b"
]

SUPERLATIVE_INDICATORS = [
    r"\bthe only\b", r"\bunprecedented\b", r"\brevolutionary\b",
    r"\buniversally proven\b", r"\bdefinitively cures\b", r"\ball scientists agree\b"
]


def calculate_citation_validity(citations: List[Any], valid_evidence_ids: Set[str]) -> float:
    """
    Evaluates what proportion of cited references correspond to real, registered evidence IDs.
    Distinguishes genuine citations from fabricated/hallucinated IDs.
    """
    if not citations:
        return 1.0  # Zero citations has 0 invalid citations, but caller may check completeness separately
    if not valid_evidence_ids:
        return 0.0

    valid_count = 0
    for cite in citations:
        cite_id = cite if isinstance(cite, str) else cite.get("evidence_id", "")
        # Extract potential ID like EV001 or ev_a_01
        matched = False
        for vid in valid_evidence_ids:
            if vid.lower() in cite_id.lower() or cite_id.lower() in vid.lower():
                matched = True
                break
        if matched:
            valid_count += 1
    return round(valid_count / len(citations), 4)


def calculate_claim_grounding_accuracy(actual_claims: List[Dict[str, Any]], expected_claims: List[Dict[str, Any]]) -> float:
    """
    Compares assigned claim statuses against expected gold-standard verdicts.
    """
    if not expected_claims:
        return 1.0
    if not actual_claims:
        return 0.0

    matches = 0
    for exp in expected_claims:
        exp_text = exp.get("claim_text", "").lower()
        exp_status = exp.get("expected_status", "SUPPORTED").upper()

        # Find matching actual claim
        for act in actual_claims:
            act_text = (act.get("claim_text") or act.get("text") or "").lower()
            act_status = (act.get("support_status") or act.get("status") or "").upper()
            if any(word in act_text for word in exp_text.split()[:4]):
                if act_status == exp_status:
                    matches += 1
                break

    return round(matches / len(expected_claims), 4)


def detect_causal_overreach(claim_text: str, is_observational_study: bool = True) -> bool:
    """
    Detects whether an observational or correlational finding is improperly framed with causal verbs.
    Returns True if causal overreach is detected.
    """
    if not is_observational_study:
        return False
    text_lower = claim_text.lower()
    for pattern in CAUSAL_INDICATORS:
        if re.search(pattern, text_lower):
            return True
    return False


def detect_superlative_overclaim(claim_text: str) -> bool:
    """
    Detects whether a claim uses ungrounded superlative or absolute scientific assertions.
    """
    text_lower = claim_text.lower()
    for pattern in SUPERLATIVE_INDICATORS:
        if re.search(pattern, text_lower):
            return True
    return False
