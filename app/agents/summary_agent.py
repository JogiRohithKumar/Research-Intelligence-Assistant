"""
Summary Agent for Research Intelligence Assistant V2.
Produces structured summaries and key findings per paper using validated Pydantic models.
"""

from typing import Any, Dict, List

from app.core.logging import logger
from app.models.state import PaperSummary, PaperSummaryList
from app.services.llm_service import generate_structured_output


def summarize_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Summarizes candidate research papers into structured items with key findings.
    Validates output using PaperSummaryList.
    """
    if not papers:
        return []

    papers_text = ""
    for i, paper in enumerate(papers, start=1):
        papers_text += f"""
Paper {i}
Title: {paper.get('title', 'Unknown')}
Abstract: {paper.get('abstract', '')}
----------------------------------------
"""

    prompt = f"""
You are an expert academic research summarizer.

Analyze EACH paper provided below individually and extract:
1. title: Exact or normalized paper title.
2. summary: Concise 2-3 sentence summary of the paper's core contribution.
3. key_findings: A list of 2 to 4 concrete empirical or theoretical findings.

Research Papers:
{papers_text}
"""
    try:
        summary_list = generate_structured_output(
            prompt=prompt,
            schema=PaperSummaryList,
            system_instruction="You are a senior scientific analyst producing concise structured paper summaries."
        )
        results = [s.model_dump() for s in summary_list.summaries]
        logger.info(f"Successfully summarized {len(results)} papers via structured LLM")
        return results
    except Exception as e:
        logger.warning(f"Structured summarization failed ({e}), constructing fallback summaries")
        fallbacks: List[Dict[str, Any]] = []
        for paper in papers:
            abstract = paper.get("abstract", "")
            snippet = abstract[:250] + ("..." if len(abstract) > 250 else "")
            fallbacks.append({
                "title": paper.get("title", "Untitled"),
                "summary": snippet or "Summary unavailable.",
                "key_findings": ["Extracted from paper abstract."]
            })
        return fallbacks