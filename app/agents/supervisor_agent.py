"""
Supervisor Agent for Research Intelligence Assistant V2.
Evaluates research question validity and determines execution routing using structured output.
"""

from app.core.logging import logger
from app.models.state import SupervisorDecision
from app.services.llm_service import generate_structured_output


def generate_supervisor_decision(query: str) -> dict:
    """
    Evaluates whether a query is suitable for academic research.
    Returns a validated dictionary conforming to SupervisorDecision.
    """
    prompt = f"""
You are the Supervisor Agent governing an academic research intelligence pipeline.

Assess the following user query for academic research suitability.
Rules:
1. If the query is vague, offensive, or non-academic (e.g. 'hello', 'tell me a joke') -> status: 'invalid', route: 'stop'.
2. If the query is research-worthy but needs academic search keyword optimization -> status: 'retry', modified_query: '<improved concise academic query>', route: 'retry_search'.
3. If the query is well-formed for academic literature retrieval -> status: 'valid', route: 'continue'.

User Query:
{query}
"""
    try:
        decision = generate_structured_output(
            prompt=prompt,
            schema=SupervisorDecision,
            system_instruction="You are a strict academic research supervisor evaluating search questions."
        )
        logger.info(f"Supervisor decision: status={decision.status}, route={decision.route}")
        return decision.model_dump()
    except Exception as e:
        logger.warning(f"Supervisor structured evaluation failed, using safe fallback: {e}")
        return {
            "status": "valid",
            "reason": "Default fallback to proceed with research query",
            "modified_query": query,
            "route": "continue"
        }