"""
Research Search Engine Orchestrator for Research Intelligence Assistant V2.
Coordinates Query Planning -> Multi-Provider Retrieval -> Deduplication -> Ranking -> Limiting.
"""

import time
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import NormalizedPaper, SearchPlan
from app.search.arxiv_provider import ArxivSearchProvider
from app.search.base import SearchProvider
from app.search.deduplication import Deduplicator
from app.search.local_provider import LocalCorpusProvider
from app.search.query_planner import QueryPlanner
from app.search.ranker import QueryRanker


class ResearchSearchEngine:
    """
    Main orchestration facade for research search and retrieval in Stage 2.
    Guarantees deterministic limits, provenance preservation, and graceful failure handling.
    """

    def __init__(
        self,
        providers: Optional[List[SearchProvider]] = None,
        planner: Optional[QueryPlanner] = None,
        deduplicator: Optional[Deduplicator] = None,
        ranker: Optional[QueryRanker] = None,
    ):
        self.settings = get_settings()
        self.planner = planner or QueryPlanner()
        self.deduplicator = deduplicator or Deduplicator()
        self.ranker = ranker or QueryRanker()

        if providers is not None:
            self.providers = providers
        else:
            self.providers = [
                ArxivSearchProvider(),
                LocalCorpusProvider(),
            ]

    def search(
        self,
        query: str,
        plan: Optional[SearchPlan] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes complete search and retrieval workflow for a user research query.
        Returns a dictionary containing 'plan', 'papers', and 'telemetry'.
        """
        start_time = time.perf_counter()
        final_limit = limit or self.settings.MAX_FINAL_RETRIEVAL_PAPERS

        # 1. Query Planning
        if plan is None:
            plan = self.planner.plan(query)

        queries_to_execute = [plan.primary_query]
        for alt in plan.alternative_queries[:self.settings.MAX_SEARCH_VARIANTS]:
            if alt and alt.lower() not in [q.lower() for q in queries_to_execute]:
                queries_to_execute.append(alt)

        # 2. Multi-Provider Retrieval
        all_candidates: List[NormalizedPaper] = []
        provider_telemetry: Dict[str, Any] = {}

        for provider in self.providers:
            p_name = provider.name
            provider_telemetry[p_name] = {"retrieved": 0, "status": "ok", "latency_ms": 0}
            p_start = time.perf_counter()

            if not provider.is_available():
                provider_telemetry[p_name]["status"] = "unavailable"
                continue

            provider_retrieved_count = 0
            for q_str in queries_to_execute:
                remaining_total = self.settings.MAX_TOTAL_CANDIDATES - len(all_candidates)
                if remaining_total <= 0:
                    break

                q_limit = min(self.settings.MAX_RESULTS_PER_PROVIDER, remaining_total)
                try:
                    results = provider.search(
                        query=q_str,
                        limit=q_limit
                    )
                    accepted = results[:remaining_total]
                    all_candidates.extend(accepted)
                    provider_retrieved_count += len(accepted)
                except Exception as p_err:
                    provider_telemetry[p_name]["status"] = f"error: {str(p_err)[:50]}"
                    logger.warning(f"Provider '{p_name}' encountered error for query '{q_str}': {p_err}")

            p_latency = int((time.perf_counter() - p_start) * 1000)
            provider_telemetry[p_name]["latency_ms"] = p_latency
            provider_telemetry[p_name]["retrieved"] = provider_retrieved_count

            if len(all_candidates) >= self.settings.MAX_TOTAL_CANDIDATES:
                break

        total_retrieved_raw = len(all_candidates)

        # 3. Deduplication
        deduped_candidates = self.deduplicator.deduplicate(all_candidates)
        dedup_count = total_retrieved_raw - len(deduped_candidates)

        # 4. Query-Dependent Ranking
        ranked_candidates = self.ranker.rank(deduped_candidates, plan)

        # 5. Result Limiting
        final_papers = ranked_candidates[:final_limit]
        total_latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Structured Telemetry
        telemetry = {
            "query": query,
            "primary_query": plan.primary_query,
            "variants_executed": len(queries_to_execute),
            "raw_candidates_count": total_retrieved_raw,
            "duplicates_removed": dedup_count,
            "ranked_count": len(ranked_candidates),
            "final_selected_count": len(final_papers),
            "provider_telemetry": provider_telemetry,
            "total_latency_ms": total_latency_ms,
        }

        top_score = final_papers[0].relevance_score if final_papers else 0.0
        logger.info(
            f"SearchEngine completed: raw={total_retrieved_raw}, deduped={len(deduped_candidates)}, "
            f"selected={len(final_papers)}, top_score={top_score}, latency={total_latency_ms}ms"
        )

        return {
            "plan": plan,
            "papers": final_papers,
            "telemetry": telemetry,
        }
