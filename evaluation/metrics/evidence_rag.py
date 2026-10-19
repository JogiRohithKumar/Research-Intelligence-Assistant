"""
Stage 3 RAG & Evidence Grounding Metrics.
Evaluates evidence relevance, provenance completeness, sufficiency, and grounding verdicts.
"""

from typing import Any, Dict, List


def calculate_evidence_relevance(retrieved_snippets: List[str], expected_keywords: List[str]) -> float:
    """
    Computes proportion of retrieved evidence snippets that contain expected core topical keywords.
    """
    if not retrieved_snippets or not expected_keywords:
        return 0.0
    relevant_count = 0
    keywords_lower = [k.lower() for k in expected_keywords]
    for snippet in retrieved_snippets:
        s_lower = snippet.lower()
        if any(kw in s_lower for kw in keywords_lower):
            relevant_count += 1
    return round(relevant_count / len(retrieved_snippets), 4)


def calculate_provenance_completeness(evidence_items: List[Dict[str, Any]]) -> float:
    """
    Evaluates what fraction of evidence objects retain complete academic provenance:
    evidence_id, paper_title, source url/doi, and non-empty text.
    """
    if not evidence_items:
        return 0.0
    complete_count = 0
    for ev in evidence_items:
        has_id = bool(ev.get("evidence_id") or ev.get("id"))
        has_title = bool(ev.get("paper_title") or ev.get("title"))
        has_source = bool(ev.get("source_url") or ev.get("doi") or ev.get("url"))
        has_text = bool(ev.get("text") or ev.get("text_snippet") or ev.get("snippet"))
        if has_id and has_title and has_source and has_text:
            complete_count += 1
    return round(complete_count / len(evidence_items), 4)


def calculate_evidence_sufficiency(actual_verdict: str, expected_verdict: str) -> float:
    """
    Evaluates whether the grounding verdict matches the expected state
    (e.g., SUPPORTED vs INSUFFICIENT_EVIDENCE).
    """
    if not actual_verdict or not expected_verdict:
        return 0.0
    return 1.0 if actual_verdict.strip().upper() == expected_verdict.strip().upper() else 0.0


def calculate_unsupported_claim_rate(claims: List[Dict[str, Any]]) -> float:
    """
    Computes the fraction of claims whose status is marked UNSUPPORTED or lack valid citing evidence.
    """
    if not claims:
        return 0.0
    unsupported_count = 0
    for cl in claims:
        status = (cl.get("support_status") or cl.get("status") or "").upper()
        citations = cl.get("citing_evidence_ids") or cl.get("citations") or []
        if status in {"UNSUPPORTED", "FABRICATED"} or not citations:
            unsupported_count += 1
    return round(unsupported_count / len(claims), 4)
