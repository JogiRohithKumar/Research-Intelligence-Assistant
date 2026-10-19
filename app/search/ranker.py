"""
Query-Dependent Relevance Ranker for Research Intelligence Assistant V2.
Computes explainable, query-specific relevance scores without hardcoded topic keywords.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Set
from app.core.logging import logger
from app.models.domain import NormalizedPaper, SearchPlan

# Standard domain-agnostic English stop words
STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "with", "as", "by", "from", "how", "what", "which",
    "that", "this", "these", "those", "effect", "impact", "study", "analysis",
    "research", "paper", "papers", "about", "can", "could", "would", "should",
    "does", "do", "i", "we", "you", "they", "me", "my", "our", "their", "via",
    "using", "based", "through", "its", "into"
}


class QueryRanker:
    """
    Ranks papers strictly against the active research query and search plan.
    Employs token overlap, title weight, concept matches, and recency.
    """

    def __init__(self):
        self.current_year = datetime.now(timezone.utc).year

    def _tokenize(self, text: str) -> List[str]:
        """Extracts non-stopword alphanumeric tokens."""
        if not text:
            return []
        cleaned = re.sub(r"[^\w\s\-]", " ", text.lower())
        tokens = [
            t.strip() for t in cleaned.split()
            if len(t.strip()) > 2 and t.strip() not in STOP_WORDS
        ]
        return tokens

    def calculate_score(
        self,
        paper: NormalizedPaper,
        plan: SearchPlan
    ) -> float:
        """
        Calculates explainable query-dependent relevance score between 0.0 and 1.0,
        and sets paper.ranking_explanation.
        """
        query_text = plan.primary_query or plan.original_query
        query_tokens = self._tokenize(query_text)

        # Fallback to normalized query tokens if query_text has few tokens
        if len(query_tokens) < 2 and plan.normalized_query:
            query_tokens = self._tokenize(plan.normalized_query)

        if not query_tokens:
            paper.relevance_score = 0.5
            paper.ranking_explanation = "neutral_relevance: no informative query tokens"
            return 0.5

        title_tokens = set(self._tokenize(paper.title))
        abstract_tokens = set(self._tokenize(paper.abstract))
        title_lower = paper.title.lower()

        # 1. Exact phrase match in title (high precision signal)
        exact_phrase_bonus = 0.0
        query_phrase = " ".join(query_tokens[:3])
        if len(query_tokens) >= 2 and query_phrase in title_lower:
            exact_phrase_bonus = 0.20

        # 2. Title token coverage (weight: 0.45)
        title_matches = sum(1 for t in query_tokens if t in title_tokens)
        title_coverage = title_matches / len(query_tokens)
        title_score = 0.45 * title_coverage

        # 3. Abstract token coverage (weight: 0.30)
        abstract_matches = sum(1 for t in query_tokens if t in abstract_tokens)
        abstract_coverage = abstract_matches / len(query_tokens)
        abstract_score = 0.30 * abstract_coverage

        # If zero token match in both title and abstract and no phrase match, score is strictly 0.0
        if title_matches == 0 and abstract_matches == 0 and exact_phrase_bonus == 0.0:
            paper.relevance_score = 0.0
            paper.ranking_explanation = "zero_overlap: no query terms matched in title or abstract"
            return 0.0

        # 4. Key Concept Matches (weight: 0.15)
        concept_matches = 0
        concepts = plan.key_concepts or []
        for concept in concepts:
            c_lower = concept.lower()
            if c_lower in title_lower or c_lower in paper.abstract.lower():
                concept_matches += 1
        concept_score = 0.15 * (min(concept_matches, 3) / max(1, min(len(concepts), 3))) if concepts else 0.0

        # 5. Publication Recency (weight: 0.05)
        recency_bonus = 0.0
        if paper.year:
            age = max(0, self.current_year - paper.year)
            if age <= 2:
                recency_bonus = 0.05
            elif age <= 5:
                recency_bonus = 0.03
            elif age <= 10:
                recency_bonus = 0.01

        # 6. Metadata Completeness Bonus (weight: 0.05)
        meta_bonus = 0.0
        if paper.doi:
            meta_bonus += 0.02
        if len(paper.authors) > 0:
            meta_bonus += 0.01
        if len(paper.abstract) > 200:
            meta_bonus += 0.02

        raw_score = (
            title_score +
            abstract_score +
            concept_score +
            exact_phrase_bonus +
            recency_bonus +
            meta_bonus
        )

        final_score = min(1.0, max(0.0, round(raw_score, 3)))
        paper.relevance_score = final_score
        paper.ranking_explanation = (
            f"title_cov={title_coverage:.2f}(score={title_score:.2f}) | "
            f"abs_cov={abstract_coverage:.2f}(score={abstract_score:.2f}) | "
            f"concepts={concept_matches}/{len(concepts)} | "
            f"phrase_match={bool(exact_phrase_bonus)} | "
            f"recency_bonus={recency_bonus:.2f} | "
            f"meta_bonus={meta_bonus:.2f}"
        )

        return final_score

    def rank(
        self,
        papers: List[NormalizedPaper],
        plan: SearchPlan
    ) -> List[NormalizedPaper]:
        """
        Scores and sorts candidate papers descending by calculated relevance score.
        """
        for paper in papers:
            self.calculate_score(paper, plan)

        ranked = sorted(papers, key=lambda p: p.relevance_score, reverse=True)
        return ranked
