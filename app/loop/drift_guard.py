"""
Query Drift Guard for Stage 5 Agentic Research Loop.
Ensures that targeted reformulations preserve parent research intent
and prevents semantic drift into unrelated domains.
"""

import re
from typing import List, Set, Tuple
from app.core.logging import logger

# Academic and grammatical stop words to ignore during topical concept extraction
STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "by", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "of", "off", "over", "under",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "can", "could", "will", "would", "should", "may", "might",
    "must", "what", "which", "who", "whom", "this", "that", "these", "those",
    "how", "why", "where", "when", "does", "effect", "impact", "influence", "role"
}


class QueryDriftGuard:
    """
    Validates that a newly generated targeted search query preserves the original
    research topic and does not drift into unrelated domains.
    """

    def extract_keywords(self, text: str) -> Set[str]:
        """Extracts significant lowercase alphanumeric tokens, stripping stop words."""
        tokens = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
        return {t for t in tokens if t not in STOP_WORDS}

    def extract_keywords_ordered(self, text: str) -> List[str]:
        """Extracts significant lowercase alphanumeric tokens preserving order, stripping stop words."""
        tokens = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
        seen = set()
        ordered = []
        for t in tokens:
            if t not in STOP_WORDS and t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered

    def check_drift(self, parent_query: str, proposed_query: str) -> Tuple[bool, float, str]:
        """
        Calculates topical anchor retention.
        Returns: (is_drift: bool, overlap_ratio: float, reason: str)
        """
        parent_keywords = self.extract_keywords(parent_query)
        proposed_keywords = self.extract_keywords(proposed_query)

        if not parent_keywords:
            return False, 1.0, "Parent query has no distinct non-stop keywords"

        shared_keywords = parent_keywords.intersection(proposed_keywords)
        overlap_ratio = len(shared_keywords) / len(parent_keywords)

        # If zero parent keywords are retained, it is a hard drift violation
        if len(shared_keywords) == 0:
            msg = (
                f"Query drift detected: Proposed query '{proposed_query}' shares zero topical "
                f"anchor terms with original query '{parent_query}'."
            )
            logger.warning(f"[Stage 5 DriftGuard] {msg}")
            return True, overlap_ratio, msg

        # If overlap is below 20% on multi-term queries and shared is only 1 token
        if len(parent_keywords) >= 4 and len(shared_keywords) < 2 and overlap_ratio < 0.25:
            msg = (
                f"Potential query drift: Low anchor retention ({overlap_ratio:.2f}) "
                f"between '{parent_query}' and '{proposed_query}'."
            )
            logger.info(f"[Stage 5 DriftGuard] {msg}")
            return True, overlap_ratio, msg

        return False, overlap_ratio, f"Acceptable topic retention ({len(shared_keywords)} shared anchors: {list(shared_keywords)[:3]})"

    def enforce_anchor(self, parent_query: str, proposed_query: str, target_concepts: List[str]) -> str:
        """
        Corrects drifted queries by firmly anchoring the parent topic with the target concepts.
        """
        parent_keywords = self.extract_keywords_ordered(parent_query)
        clean_concepts = [c.strip() for c in target_concepts if c.strip() and c.strip().lower() not in STOP_WORDS]

        # Build anchored query
        core_parent = " ".join(parent_keywords[:5])
        core_gap = " ".join(clean_concepts[:3])

        anchored = f"{core_parent} {core_gap}".strip()
        logger.info(f"[Stage 5 DriftGuard] Anchored drifted query to: '{anchored}'")
        return anchored

    def is_drifted(self, original_query: str, candidate_query: str) -> bool:
        """Returns True if candidate_query has drifted away from original_query."""
        drift, _, _ = self.check_drift(original_query, candidate_query)
        return drift


DriftGuard = QueryDriftGuard
