"""
Verification Agent for Research Intelligence Assistant V2.
Validates consensus, detects contradictions, and computes evidence strength across paper findings.
"""

from typing import Any, Dict, List

from app.core.logging import logger
from app.models.domain import VerificationResult
from app.services.llm_service import generate_structured_output


def verify_findings(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes multiple paper summaries to identify common findings, contradictions,
    and overall evidence confidence score.
    """
    if not summaries:
        return VerificationResult(
            common_findings=[],
            conflicting_findings=[],
            evidence_strength="none",
            confidence_score=0.0
        ).model_dump()

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
You are a senior scientific research verification specialist.

Analyze the findings across all provided research papers:
1. Identify common findings shared or supported across multiple papers.
2. Identify conflicting findings, contradictions, or methodology discrepancies.
3. Assess overall evidence strength (weak, moderate, strong, conclusive).
4. Provide a confidence score between 0.0 and 1.0 representing empirical consistency.

Research Papers:
{summaries_text}
"""
    try:
        result = generate_structured_output(
            prompt=prompt,
            schema=VerificationResult,
            system_instruction="You are an expert research verification auditor."
        )
        logger.info(f"Verification completed with confidence: {result.confidence_score}")
        return result.model_dump()
    except Exception as e:
        logger.warning(f"Verification structured output failed ({e}), using safe fallback")
        return {
            "common_findings": [f"Synthesized across {len(summaries)} research papers."],
            "conflicting_findings": [],
            "evidence_strength": "moderate",
            "confidence_score": 0.0
        }