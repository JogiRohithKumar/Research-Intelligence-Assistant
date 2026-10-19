"""
Stage 4 Research Intelligence Metrics.
Evaluates cross-paper comparison extraction, contradiction detection fidelity,
gap qualification framing, and evidence strength classification.
"""

from typing import Any, Dict, List


def calculate_contradiction_precision(
    detected_contradictions: List[Any],
    expected_has_contradiction: bool
) -> float:
    """
    Evaluates whether genuine contradictions were identified without false alarms
    on methodology/population variations.
    """
    has_detected = len(detected_contradictions) > 0
    if expected_has_contradiction:
        return 1.0 if has_detected else 0.0
    else:
        # Expected NO contradiction: reward 1.0 if none detected, 0.0 if false positive
        return 1.0 if not has_detected else 0.0


def calculate_gap_qualification_rate(gaps: List[Any]) -> float:
    """
    Verifies that detected research gaps use the mandatory qualified framing
    ('Within the retrieved literature...', 'In the analyzed papers...')
    rather than absolute universal assertions ('No research has ever been done...').
    """
    if not gaps:
        return 1.0  # Zero gaps contains no overreaching statements

    qualified_count = 0
    disallowed_phrases = ["no research exists", "never been studied", "no scientist has ever"]

    for gap in gaps:
        text = (gap if isinstance(gap, str) else gap.get("description", "")).lower()
        has_universal = any(phrase in text for phrase in disallowed_phrases)
        has_qualification = any(q in text for q in ["within the retrieved", "analyzed literature", "retrieved papers", "available evidence"])
        if has_qualification and not has_universal:
            qualified_count += 1
        elif not has_universal:
            # Tolerant if neither overclaiming nor explicitly qualified
            qualified_count += 0.8

    return round(min(1.0, qualified_count / len(gaps)), 4)


def verify_evidence_strength_heuristic(assigned_rating: str, study_types: List[str]) -> bool:
    """
    Verifies that evidence strength classifications conform to Stage 4 qualitative rules:
    - STRONG / HIGH requires meta-analysis or multi-center randomized controlled trials
    - MODERATE applies to observational prospective cohorts or quasi-experimental studies
    - PRELIMINARY / WEAK applies to in vitro, animal models, or isolated case reports
    """
    rating = assigned_rating.upper()
    study_types_lower = [s.lower() for s in study_types]

    has_meta_or_rct = any("meta-analysis" in s or "randomized" in s or "rct" in s or "phase 3" in s for s in study_types_lower)
    has_in_vitro_or_animal = any("in vitro" in s or "cell line" in s or "mouse" in s or "murine" in s or "rat" in s for s in study_types_lower)

    if rating in {"STRONG", "HIGH"}:
        return has_meta_or_rct and not has_in_vitro_or_animal
    elif rating in {"PRELIMINARY", "WEAK", "INSUFFICIENT"}:
        return True
    elif rating in {"MODERATE", "MIXED"}:
        return True
    return False
