"""
Query Planner for Research Intelligence Assistant V2.
Canonical source of truth for query decomposition, variant generation,
and concept extraction.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import SearchPlan
from app.services.llm_service import generate_structured_output

# Common English stop words to ignore during concept extraction
STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "with", "as", "by", "from", "how", "what", "which",
    "that", "this", "these", "those", "effect", "impact", "study", "analysis",
    "research", "paper", "papers", "about", "can", "could", "would", "should",
    "does", "do", "i", "we", "you", "they", "me", "my", "our", "their"
}


class LLMQueryPlanOutput(BaseModel):
    """Structured LLM schema for query planning."""
    primary_query: str = Field(..., description="Concise academic search query under 10 words")
    alternative_queries: List[str] = Field(default_factory=list, description="1-3 alternative academic query variants")
    key_concepts: List[str] = Field(default_factory=list, description="3-6 core technical terms or concepts")
    intent: str = Field(default="scholarly_literature_review", description="Academic research intent")


class QueryPlanner:
    """
    Produces a single canonical SearchPlan for incoming research topics.
    Uses structured LLM generation with a deterministic academic fallback.
    """

    def __init__(self):
        self.settings = get_settings()

    def normalize_query(self, query: str) -> str:
        """Strips excessive whitespace, punctuation, and converts to lowercase."""
        cleaned = re.sub(r"[^\w\s\-\.]", " ", query)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
        return cleaned

    def extract_heuristic_concepts(self, query: str) -> List[str]:
        """Deterministic fallback extraction of key academic concepts."""
        tokens = [
            t.strip(".,;:?!'\"()[]{}")
            for t in query.split()
            if len(t) > 2 and t.lower() not in STOP_WORDS
        ]
        # Preserve multi-word combinations if available
        concepts = []
        for i in range(len(tokens)):
            if tokens[i].lower() not in [c.lower() for c in concepts]:
                concepts.append(tokens[i])
        return concepts[:6]

    def create_fallback_plan(self, query: str) -> SearchPlan:
        """Deterministic plan created without calling an external LLM."""
        normalized = self.normalize_query(query)
        concepts = self.extract_heuristic_concepts(query)

        # Primary query from key concepts
        primary = " ".join(concepts[:5]) if concepts else normalized
        if not primary:
            primary = "scientific research"

        # Alternative query variants
        alternatives = []
        if len(concepts) >= 2:
            alternatives.append(f"{concepts[0]} {concepts[1]} methodology")
        if len(concepts) >= 3:
            alternatives.append(f"{concepts[1]} {concepts[2]} survey")
        elif len(concepts) == 1:
            alternatives.append(f"{concepts[0]} overview")

        # Cap alternative queries according to configuration
        max_variants = max(1, self.settings.MAX_SEARCH_VARIANTS)
        alternatives = alternatives[:max_variants]

        return SearchPlan(
            original_query=query,
            normalized_query=normalized,
            primary_query=primary,
            alternative_queries=alternatives,
            key_concepts=concepts,
            intent="scholarly_literature_review",
            retrieval_strategy="hybrid_academic",
            filters={}
        )

    def plan(self, query: str) -> SearchPlan:
        """
        Generates canonical SearchPlan using structured LLM if available,
        falling back gracefully to deterministic heuristics.
        """
        trimmed = query.strip()
        if not trimmed:
            return self.create_fallback_plan("empty query")

        normalized = self.normalize_query(trimmed)

        # Attempt structured LLM query planning
        prompt = f"""You are a scientific literature retrieval specialist.
Analyze the following user research query and generate a structured academic search plan.

User Query: "{trimmed}"

Instructions:
1. primary_query: Formulate an optimized scholarly search query (under 10 words, focusing on domain-specific technical terminology).
2. alternative_queries: Provide up to {self.settings.MAX_SEARCH_VARIANTS} alternative academic queries using formal synonyms or related sub-aspects.
3. key_concepts: Extract 3-6 specific academic entities, methods, or phenomena.
4. intent: Describe the research intent (e.g., 'empirical_evaluation', 'survey_review', 'mechanistic_analysis').
"""
        try:
            llm_result: Optional[LLMQueryPlanOutput] = generate_structured_output(
                prompt=prompt,
                schema=LLMQueryPlanOutput,
                system_instruction="You are an expert scientific search planner. Produce strict academic search plans."
            )
            if llm_result and llm_result.primary_query:
                # Cap alternative variants
                max_vars = self.settings.MAX_SEARCH_VARIANTS
                alt_queries = [
                    q.strip() for q in llm_result.alternative_queries
                    if q.strip() and q.strip().lower() != llm_result.primary_query.strip().lower()
                ][:max_vars]

                plan = SearchPlan(
                    original_query=trimmed,
                    normalized_query=normalized,
                    primary_query=llm_result.primary_query.strip(),
                    alternative_queries=alt_queries,
                    key_concepts=[c.strip() for c in llm_result.key_concepts if c.strip()],
                    intent=llm_result.intent or "scholarly_literature_review",
                    retrieval_strategy="hybrid_academic",
                    filters={}
                )
                logger.info(f"QueryPlanner generated plan for '{trimmed[:40]}...' (primary: '{plan.primary_query}')")
                return plan
        except Exception as e:
            logger.warning(f"Structured LLM query planning failed ({e}); using deterministic fallback")

        # Fallback plan
        fallback = self.create_fallback_plan(trimmed)
        logger.info(f"QueryPlanner generated heuristic fallback plan for '{trimmed[:40]}...'")
        return fallback
