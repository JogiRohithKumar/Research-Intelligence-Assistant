"""
Targeted Query Planner for Stage 5 Agentic Research Loop.
Formulates gap-specific search queries using structured strategies,
enforcing intent preservation, drift prevention, and duplicate detection.
"""

import re
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import (
    ActionableResearchGap,
    TargetedResearchQuery,
)
from app.loop.drift_guard import QueryDriftGuard
from app.utils.safe_execute import safe_execute

try:
    from google.genai import types
    from app.services.llm_service import get_gemini_client
except ImportError:
    types = None
    get_gemini_client = None


class LLMTargetedQueryProposal(BaseModel):
    query_text: str = Field(..., description="Targeted academic search query under 12 words preserving original topic")
    target_concepts: List[str] = Field(default_factory=list, description="Specific missing concepts or keywords targeted")
    strategy_used: str = Field(default="EVIDENCE_GAP", description="Strategy type (POPULATION_FOCUSED, METHODOLOGY_FOCUSED, etc.)")
    rationale: str = Field(default="", description="Why this reformulation addresses the specific gap")


class TargetedQueryPlanner:
    """
    Plans and generates targeted research queries to resolve specific research gaps.
    """

    def __init__(self):
        self.settings = get_settings()
        self.drift_guard = QueryDriftGuard()

    def plan_targeted_query(
        self,
        parent_query: str,
        gap: ActionableResearchGap,
        executed_queries: List[str],
        iteration: int
    ) -> TargetedResearchQuery:
        """
        Synthesizes a targeted research query directed at the specified gap.
        Ensures topic fidelity via QueryDriftGuard and avoids repeating past queries.
        """
        strategy = self._map_gap_to_strategy(gap.category)

        # 1. Attempt structured LLM query generation
        llm_proposal = self._generate_with_llm(parent_query, gap, strategy)

        if llm_proposal and llm_proposal.query_text:
            candidate_query = llm_proposal.query_text.strip()
            target_concepts = llm_proposal.target_concepts or self._extract_gap_concepts(gap.description)
            rationale = llm_proposal.rationale or f"Targeting {gap.category} using {strategy} strategy"
        else:
            # 2. Resilient deterministic heuristic fallback
            candidate_query, target_concepts, rationale = self._generate_heuristic(
                parent_query, gap, strategy
            )

        # 3. Query Drift Guard Check
        is_drift, overlap, reason = self.drift_guard.check_drift(parent_query, candidate_query)
        if is_drift:
            logger.warning(f"[Stage 5 QueryPlanner] Drift detected in proposed query '{candidate_query}'. Enforcing parent topic anchor.")
            candidate_query = self.drift_guard.enforce_anchor(parent_query, candidate_query, target_concepts)

        # 4. Duplicate Query Check
        candidate_query = self._ensure_non_duplicate(candidate_query, parent_query, executed_queries, target_concepts)

        targeted_query = TargetedResearchQuery(
            query_id=f"TRQ_{uuid.uuid4().hex[:6]}",
            parent_query=parent_query,
            gap_addressed_id=gap.gap_id,
            query_text=candidate_query,
            rationale=rationale,
            target_concepts=target_concepts,
            strategy=strategy,
            iteration=iteration
        )

        logger.info(
            f"[Stage 5 QueryPlanner] Iteration {iteration} planned: '{candidate_query}' "
            f"(Strategy={strategy}, Gap={gap.gap_id})"
        )
        return targeted_query

    def _map_gap_to_strategy(self, category: str) -> str:
        """Maps an actionable gap category to a search reformulation strategy."""
        cat = category.upper()
        if "POPULATION" in cat:
            return "POPULATION_FOCUSED"
        elif "DATASET" in cat:
            return "MISSING_DATASET"
        elif "METHOD" in cat:
            return "METHODOLOGY_FOCUSED"
        elif "OUTCOME" in cat:
            return "OUTCOME_FOCUSED"
        elif "CONTRADICTION" in cat:
            return "CONTRADICTION_FOCUSED"
        elif "UNSUPPORTED" in cat:
            return "UNSUPPORTED_CLAIM"
        elif "GENERALIZATION" in cat:
            return "TERMINOLOGY_EXPANSION"
        return "EVIDENCE_GAP"

    def _extract_gap_concepts(self, gap_description: str) -> List[str]:
        """Extracts significant keywords from a gap description."""
        clean = re.sub(r"Within the retrieved literature,?\s*", "", gap_description, flags=re.IGNORECASE)
        clean = re.sub(r"[^a-zA-Z0-9\s_-]", " ", clean)
        tokens = [t.strip().lower() for t in clean.split() if len(t.strip()) > 3]
        stop_words = {"about", "there", "their", "where", "which", "study", "studies", "literature", "retrieved"}
        return [t for t in tokens if t not in stop_words][:5]

    def _generate_heuristic(
        self,
        parent_query: str,
        gap: ActionableResearchGap,
        strategy: str
    ) -> tuple[str, List[str], str]:
        """Deterministic heuristic generator guaranteed to work without network/LLM."""
        gap_concepts = self._extract_gap_concepts(gap.description)
        parent_words = [w for w in parent_query.split() if len(w) > 3][:6]

        # Strategic keyword injection based on gap type
        focus_terms: List[str] = []
        if strategy == "POPULATION_FOCUSED":
            focus_terms = gap_concepts[:2] or ["clinical", "human cohort"]
        elif strategy == "MISSING_DATASET":
            focus_terms = gap_concepts[:2] or ["benchmark", "evaluation dataset"]
        elif strategy == "METHODOLOGY_FOCUSED":
            focus_terms = gap_concepts[:2] or ["experimental design", "methodology"]
        elif strategy == "OUTCOME_FOCUSED":
            focus_terms = gap_concepts[:2] or ["long term outcome", "metrics"]
        elif strategy == "CONTRADICTION_FOCUSED":
            focus_terms = ["comparative analysis", "meta analysis"]
        elif strategy == "UNSUPPORTED_CLAIM":
            focus_terms = gap_concepts[:3]
        else:
            focus_terms = gap_concepts[:2]

        anchored_query = " ".join(parent_words + focus_terms).strip()
        rationale = f"Heuristic reformulation targeting {gap.category} ({strategy})"
        return anchored_query, focus_terms, rationale

    def _generate_with_llm(
        self,
        parent_query: str,
        gap: ActionableResearchGap,
        strategy: str
    ) -> Optional[LLMTargetedQueryProposal]:
        """Generates targeted query using Gemini structured output with safe execution."""
        if not get_gemini_client or not types:
            return None

        prompt = f"""You are the Targeted Query Planner for an academic research loop.
Current Original Query: "{parent_query}"
Identified Research Gap:
- Category: {gap.category}
- Description: {gap.description}
- Recommended Action: {gap.recommended_research_action}

Strategy to use: {strategy}

Requirements:
1. Generate an academic search query (maximum 10-12 words).
2. The query MUST strictly preserve the core subject of the original research question (DO NOT drift to an unrelated domain).
3. The query MUST incorporate the missing dimension (population, dataset, metric, or comparative technique) identified in the gap.
4. Output valid JSON adhering to the schema.
"""

        def _call_gemini():
            client = get_gemini_client()
            response = client.models.generate_content(
                model=self.settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LLMTargetedQueryProposal,
                    temperature=0.2,
                )
            )
            return LLMTargetedQueryProposal.model_validate_json(response.text)

        result = safe_execute("Targeted Query Planner", _call_gemini)
        if result["success"] and result["result"]:
            return result["result"]

        return None

    def _ensure_non_duplicate(
        self,
        candidate_query: str,
        parent_query: str,
        executed_queries: List[str],
        target_concepts: List[str]
    ) -> str:
        """
        Detects if candidate_query has already been executed.
        If duplicate or near-duplicate, modifies query tokens to differentiate.
        """
        def normalize(q: str) -> str:
            return " ".join(sorted(re.sub(r"[^a-zA-Z0-9]", "", w.lower()) for w in q.split()))

        norm_cand = normalize(candidate_query)
        executed_norms = [normalize(q) for q in executed_queries]

        if norm_cand in executed_norms or candidate_query.lower() in [q.lower() for q in executed_queries]:
            logger.info(f"[Stage 5 QueryPlanner] Query '{candidate_query}' was already executed. Modifying with synonym/strategy expansion.")
            # Inject distinct qualifier to avoid exact duplicate search
            modifier = "empirical study" if "empirical" not in candidate_query.lower() else "comparative evaluation"
            candidate_query = f"{candidate_query} {modifier}".strip()

        return candidate_query
