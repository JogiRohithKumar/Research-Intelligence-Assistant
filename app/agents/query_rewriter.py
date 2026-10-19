"""
Query Rewriter Agent for Research Intelligence Assistant V2.
Transforms user research topics into targeted academic search queries.
"""

from app.core.logging import logger
from app.services.llm_service import generate_text


def rewrite_query(query: str) -> str:
    """
    Transforms natural language research questions into concise academic search queries.
    Gracefully falls back to original query on any failure.
    """
    prompt = f"""
Convert the following research topic into an optimized, concise academic search query suitable for arXiv and scientific literature databases.

Rules:
- Include essential domain keywords and academic synonyms.
- Avoid stop words, conversational filler, and punctuation.
- Keep the final search query under 12 words.
- Return ONLY the search query string, nothing else.

Topic:
{query}
"""
    try:
        optimized = generate_text(
            prompt=prompt,
            system_instruction="You are an expert scientific literature search specialist."
        )
        # Clean any quotes or multiple lines
        cleaned = optimized.replace('"', "").replace("\n", " ").strip()
        if cleaned:
            logger.info(f"Query rewritten: '{query}' -> '{cleaned}'")
            return cleaned
    except Exception as e:
        logger.warning(f"Query rewriting failed ({e}); falling back to original query")

    return query