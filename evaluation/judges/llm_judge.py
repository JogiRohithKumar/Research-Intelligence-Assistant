"""
Controlled LLM-as-Judge Layer for Stage 8.
Applies a strict, structured peer-review rubric while blinding system identity.
Maintains clear separation between automated deterministic metrics and heuristic judge scores.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.services.llm_service import generate_structured_output


class JudgeEvaluationResult(BaseModel):
    """Structured rubric output from blinded LLM peer referee."""
    faithfulness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Degree to which the claim is factually grounded in cited excerpts (1.0 = fully faithful, 0.0 = fabricated)"
    )
    hallucination_detected: bool = Field(
        ...,
        description="True if claim asserts facts, numbers, or conclusions absent from the source excerpts"
    )
    causal_overreach_detected: bool = Field(
        ...,
        description="True if observational correlation is misrepresented as causal mechanism"
    )
    unsupported_inference: bool = Field(
        ...,
        description="True if claim makes speculative leaps beyond what evidence warrants"
    )
    reasoning_rationale: str = Field(
        ...,
        description="Concise, objective explanation referencing specific excerpts"
    )


class LLMJudge:
    """
    Blinded LLM Peer Review Referee.
    Evaluates complex synthesis nuance without self-referential bias.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or "gemini-2.5-flash"

    def judge_claim_faithfulness(
        self,
        claim_text: str,
        evidence_snippets: List[str]
    ) -> JudgeEvaluationResult:
        """
        Submits blinded prompt to structured judge with strict evaluation rubric.
        Falls back safely to conservative deterministic judgment if LLM API is unavailable.
        """
        joined_evidence = "\n---\n".join(evidence_snippets)
        prompt = f"""You are an impartial, blinded scientific peer reviewer.
Evaluate whether the following CANDIDATE CLAIM is factually supported by the provided SOURCE EXCERPTS.

[SOURCE EXCERPTS]
{joined_evidence}

[CANDIDATE CLAIM]
"{claim_text}"

EVALUATION RUBRIC:
1. Base your evaluation EXCLUSIVELY on the provided source excerpts.
2. faithfulness_score: 1.0 if all figures and assertions match exactly; 0.5 if partially supported; 0.0 if contradicted or ungrounded.
3. hallucination_detected: True if the claim introduces numbers, mechanisms, or findings absent from the excerpts.
4. causal_overreach_detected: True if observational data is described as causal prevention/cure.
5. unsupported_inference: True if the claim leaps to broad generalizations not stated in the excerpts.
"""
        try:
            return generate_structured_output(
                prompt=prompt,
                schema=JudgeEvaluationResult,
                system_instruction="You are a strict, objective scientific peer review judge."
            )
        except Exception as e:
            # Deterministic, safe fallback rubric
            words = claim_text.lower().split()
            evidence_blob = joined_evidence.lower()
            overlap = sum(1 for w in words if len(w) > 4 and w in evidence_blob)
            ratio = overlap / max(1, len([w for w in words if len(w) > 4]))
            is_faithful = ratio >= 0.5

            return JudgeEvaluationResult(
                faithfulness_score=round(min(1.0, ratio), 2),
                hallucination_detected=not is_faithful,
                causal_overreach_detected=("causes" in claim_text.lower() or "prevents" in claim_text.lower()),
                unsupported_inference=not is_faithful,
                reasoning_rationale=f"Deterministic fallback evaluation based on term overlap ratio ({ratio:.2f}) due to LLM provider state: {e}"
            )
