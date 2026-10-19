"""
Search and Retrieval Engine for Research Intelligence Assistant V2 (Stage 2).
Provides query planning, scholarly search provider abstraction,
deterministic deduplication, query-dependent ranking, and retrieval telemetry.
"""

from app.search.base import SearchProvider
from app.search.query_planner import QueryPlanner
from app.search.arxiv_provider import ArxivSearchProvider
from app.search.local_provider import LocalCorpusProvider
from app.search.deduplication import Deduplicator
from app.search.ranker import QueryRanker
from app.search.engine import ResearchSearchEngine

__all__ = [
    "SearchProvider",
    "QueryPlanner",
    "ArxivSearchProvider",
    "LocalCorpusProvider",
    "Deduplicator",
    "QueryRanker",
    "ResearchSearchEngine",
]
