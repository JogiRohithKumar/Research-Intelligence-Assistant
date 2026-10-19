"""
Grounded Synthesis Agent for Research Intelligence Assistant V2 (Stage 3).
Transforms retrieved evidence into verified factual claims with explicit evidence mapping.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.models.domain import (
    CitationVerificationResult,
    ClaimSupportStatus,
    ClaimType,
    EvidenceChunk,
    ResearchClaim,
)
from app.rag.claim_validator import CitationVerifier
from app.rag.context_builder import EvidenceContextBuilder
from app.rag.evidence import EvidenceRegistry
from app.services.llm_service import generate_structured_output


class LLMClaimItem(BaseModel):
    """Schema for individual claims extracted by LLM."""
    claim_id: str = Field(..., description="Sequential ID e.g. C001, C002")
    claim_text: str = Field(..., description="Factual proposition directly supported by evidence")
    claim_type: str = Field(default="empirical_finding", description="empirical_finding, methodological, theoretical, or limitation")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of supporting evidence chunks e.g. ['E001']")
    exact_quotes: List[str] = Field(default_factory=list, description="Verbatim quote excerpts if quoting directly")


class LLMGroundedSynthesis(BaseModel):
    """Schema for structured LLM grounded synthesis output."""
    claims: List[LLMClaimItem] = Field(default_factory=list)
    grounded_summary: str = Field(default="", description="Grounded synthesis narrative citing evidence IDs in square brackets")
    insufficient_evidence_aspects: List[str] = Field(default_factory=list, description="Query aspects not supported by retrieved evidence")


def synthesize_grounded_research(
    query: str,
    registry: EvidenceRegistry
) -> Dict[str, Any]:
    """
    Generates evidence-grounded research claims and narrative synthesis.
    Validates all claims and citations against the active EvidenceRegistry.
    """
    if registry.count() == 0:
        logger.warning(f"No evidence in registry for query '{query}'; returning insufficient evidence state")
        return {
            "claims": [],
            "grounded_summary": "The retrieved literature does not provide sufficient evidence to support factual claims on this topic.",
            "verification": CitationVerificationResult(
                grounding_status="UNGROUNDED",
                notes=["No verified evidence chunks were retrieved."]
            ).model_dump(),
            "insufficient_evidence_aspects": [query]
        }

    builder = EvidenceContextBuilder()
    evidence_context = builder.build_context(registry)
    grounding_rules = builder.get_grounding_instructions()

    prompt = f"""You are a rigorous scientific research intelligence analyst.
Analyze the following query and synthesize evidence-grounded research claims based EXCLUSIVELY on the provided evidence blocks.

Research Query: "{query}"

Retrieved Source Evidence:
{evidence_context}

{grounding_rules}

Instructions:
1. For each factual research claim, assign an ID (C001, C002, ...) and list the supporting evidence ID(s) (e.g. ['E001']).
2. Every claim MUST be directly substantiated by the text of the cited evidence chunk(s).
3. Do NOT cite evidence IDs that are not present in the context above.
4. If a claim contains direct quotes, provide the exact quote text in 'exact_quotes'.
5. If the evidence does not answer key parts of the research query, list them under 'insufficient_evidence_aspects'.
"""

    raw_claims: List[ResearchClaim] = []
    grounded_summary = ""
    insufficient_aspects: List[str] = []

    try:
        output: Optional[LLMGroundedSynthesis] = generate_structured_output(
            prompt=prompt,
            schema=LLMGroundedSynthesis,
            system_instruction="You are an evidence-grounded research assistant. Never fabricate claims or citations."
        )
        if output and output.claims:
            grounded_summary = output.grounded_summary
            insufficient_aspects = output.insufficient_evidence_aspects

            for c in output.claims:
                # Map string claim_type to Enum
                c_type = ClaimType.EMPIRICAL_FINDING
                if c.claim_type.lower() in [ct.value for ct in ClaimType]:
                    c_type = ClaimType(c.claim_type.lower())

                claim_obj = ResearchClaim(
                    claim_id=c.claim_id,
                    claim_text=c.claim_text,
                    claim_type=c_type,
                    evidence_ids=c.evidence_ids,
                    exact_quotes=c.exact_quotes
                )
                raw_claims.append(claim_obj)

            logger.info(f"LLM generated {len(raw_claims)} structured research claims")
    except Exception as e:
        logger.warning(f"Structured claim generation failed ({e}); constructing deterministic claims from evidence")

    # Deterministic fallback if LLM was unavailable or produced 0 claims
    if not raw_claims:
        chunks = registry.all_chunks()[:5]
        for idx, chunk in enumerate(chunks, 1):
            claim_id = f"C{idx:03d}"
            # Extract first sentence as factual finding
            first_sentence = chunk.text.split(". ")[0].strip() + "."
            raw_claims.append(
                ResearchClaim(
                    claim_id=claim_id,
                    claim_text=f"Evidence from {chunk.title}: {first_sentence}",
                    claim_type=ClaimType.EMPIRICAL_FINDING,
                    evidence_ids=[chunk.evidence_id],
                    exact_quotes=[]
                )
            )
        grounded_summary = f"Synthesized findings from {len(chunks)} verified evidence excerpts addressing '{query}'."

    # Verify all claims, citations, and quote integrity
    verifier = CitationVerifier()
    verification_result = verifier.verify_all(raw_claims, registry)

    # Filter to only supported / grounded claims for primary findings
    valid_claims = [c for c in raw_claims if c.support_status in (ClaimSupportStatus.SUPPORTED, ClaimSupportStatus.PARTIALLY_SUPPORTED)]

    logger.info(
        f"Grounded synthesis completed: {len(valid_claims)}/{len(raw_claims)} claims verified. "
        f"Grounding status: {verification_result.grounding_status}"
    )

    return {
        "claims": [c.model_dump() for c in raw_claims],
        "supported_claims": [c.model_dump() for c in valid_claims],
        "grounded_summary": grounded_summary,
        "verification": verification_result.model_dump(),
        "insufficient_evidence_aspects": insufficient_aspects,
    }
