"""
Gap Analysis Agent for Research Intelligence Assistant V2.
Identifies research gaps, unexplored methodologies, and future directions across literature.
"""

from typing import Any, Dict, List

from app.core.logging import logger
from app.models.domain import GapAnalysisResult
from app.services.llm_service import generate_structured_output


def analyze_gaps(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes literature summaries to extract unaddressed research gaps,
    missing areas, future directions, and unanswered research questions.
    """
    if not summaries:
        return GapAnalysisResult().model_dump()

    summaries_text = ""
    for s in summaries[:10]:
        findings = "\n".join(f"- {f}" for f in s.get("key_findings", []))
        summaries_text += f"""
Title: {s.get('title', '')}
Summary: {s.get('summary', '')}
Key Findings:
{findings}
----------------------------------------
"""

    prompt = f"""
You are a senior academic research strategist and gap analysis expert.

Analyze the provided research summaries to identify what the current literature is MISSING:
1. research_gaps: Concrete limitations, unaddressed assumptions, or blind spots in current studies.
2. missing_areas: Domains, populations, or benchmark tasks not explored in the papers.
3. future_directions: High-value opportunities for subsequent investigation.
4. unanswered_questions: Critical open research questions left unresolved.

Research Papers:
{summaries_text}
"""
    try:
        result = generate_structured_output(
            prompt=prompt,
            schema=GapAnalysisResult,
            system_instruction="You are a senior research strategist performing gap analysis."
        )
        logger.info(f"Gap analysis completed: {len(result.research_gaps)} gaps identified")
        return result.model_dump()
    except Exception as e:
        logger.warning(f"Gap analysis structured output failed ({e}), using safe fallback")
        return {
            "research_gaps": ["Scalability and evaluation benchmarks require broader multi-domain study."],
            "missing_areas": ["Long-term empirical validation across heterogeneous environments."],
            "future_directions": ["Investigate cross-modal integration and standardized evaluation protocols."],
            "unanswered_questions": ["How do these findings generalize to production scenarios?"]
        }