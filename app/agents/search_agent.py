"""
Search Agent for Research Intelligence Assistant V2.
Delegates retrieval to ResearchSearchEngine and formats canonical normalized paper records.
"""

from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import NormalizedPaper, SearchPlan
from app.search.engine import ResearchSearchEngine
from app.search.ranker import QueryRanker

_search_engine: Optional[ResearchSearchEngine] = None


def get_search_engine() -> ResearchSearchEngine:
    """Returns singleton ResearchSearchEngine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = ResearchSearchEngine()
    return _search_engine


def calculate_query_relevance(paper: Dict[str, Any], query: str) -> float:
    """
    Backwards-compatible query relevance calculation.
    Uses QueryRanker to evaluate paper relevance without hardcoded topic keywords.
    """
    ranker = QueryRanker()
    mock_paper = NormalizedPaper(
        id=paper.get("id", "paper"),
        paper_id=paper.get("id", "paper"),
        title=paper.get("title", ""),
        authors=paper.get("authors", []),
        abstract=paper.get("abstract", ""),
        published=paper.get("published", ""),
        paper_url=paper.get("paper_url", ""),
        doi=paper.get("doi")
    )
    plan = SearchPlan(
        original_query=query,
        normalized_query=query.lower(),
        primary_query=query,
        alternative_queries=[],
        key_concepts=[],
        intent="scholarly_literature_review"
    )
    return ranker.calculate_score(mock_paper, plan)


def search_papers(
    query: str,
    search_plan: Optional[SearchPlan] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Executes search and retrieval using the Stage 2 ResearchSearchEngine.
    Returns serialized NormalizedPaper records.
    """
    engine = get_search_engine()
    result = engine.search(query=query, plan=search_plan, limit=limit)
    papers: List[NormalizedPaper] = result.get("papers", [])

    # Return list of dictionaries conforming to NormalizedPaper / CandidatePaper
    return [p.model_dump() for p in papers]
