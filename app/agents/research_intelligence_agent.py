"""
Research Intelligence Coordinator Agent for Research Intelligence Assistant V2 (Stage 4).
Orchestrates deep cross-paper analysis, agreement & contradiction detection,
methodology comparison, evidence strength assessment, and grounded consensus synthesis.
"""

from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.intelligence.engine import ResearchIntelligenceEngine
from app.models.domain import EvidenceChunk, ResearchClaim


def generate_research_intelligence(
    query: str,
    summaries: Optional[List[Dict[str, Any]]] = None,
    citations: Optional[List[Dict[str, Any]]] = None,
    papers: Optional[List[Dict[str, Any]]] = None,
    evidence_registry: Optional[List[Dict[str, Any]]] = None,
    claims: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Coordinates modular Stage 4 research intelligence execution.
    Consumes Stage 3 validated claims and EvidenceChunks.
    Guarantees full backward compatibility with callers passing (query, summaries, citations).
    """
    summaries = summaries or []
    citations = citations or []
    papers = papers or []
    evidence_registry = evidence_registry or []
    claims_data = claims or []

    # If papers not explicitly provided, fall back to summaries
    if not papers and summaries:
        papers = summaries

    # Reconstruct typed EvidenceChunk objects
    parsed_evidence: List[EvidenceChunk] = []
    for item in evidence_registry:
        if isinstance(item, EvidenceChunk):
            parsed_evidence.append(item)
        elif isinstance(item, dict):
            try:
                parsed_evidence.append(EvidenceChunk.model_validate(item))
            except Exception as e:
                logger.warning(f"Failed to validate EvidenceChunk in intelligence agent: {e}")

    # Fallback evidence from papers/summaries if registry was empty
    if not parsed_evidence and papers:
        for p in papers:
            pid = p.get("paper_id") or p.get("id") or "paper_unknown"
            title = p.get("title", "Untitled")
            abstract = p.get("abstract") or p.get("summary") or ""
            if abstract:
                parsed_evidence.append(
                    EvidenceChunk(
                        evidence_id=f"E_{pid[:8]}",
                        paper_id=pid,
                        chunk_id=f"paper:{pid}:chunk:0_abs",
                        text=abstract,
                        title=title,
                    )
                )

    # Reconstruct typed ResearchClaim objects
    parsed_claims: List[ResearchClaim] = []
    for item in claims_data:
        if isinstance(item, ResearchClaim):
            parsed_claims.append(item)
        elif isinstance(item, dict):
            try:
                parsed_claims.append(ResearchClaim.model_validate(item))
            except Exception as e:
                logger.warning(f"Failed to validate ResearchClaim in intelligence agent: {e}")

    # Fallback claims from paper summaries if claims list was empty
    if not parsed_claims and summaries:
        for idx, s in enumerate(summaries, 1):
            findings = s.get("key_findings", [])
            summary_text = s.get("summary", "")
            title = s.get("title", "")
            pid = s.get("paper_id") or s.get("id") or f"P{idx:03d}"
            
            matching_eids = [e.evidence_id for e in parsed_evidence if e.paper_id == pid] or (
                [parsed_evidence[0].evidence_id] if parsed_evidence else []
            )

            if findings:
                for f_idx, finding in enumerate(findings[:2], 1):
                    parsed_claims.append(
                        ResearchClaim(
                            claim_id=f"C{len(parsed_claims)+1:03d}",
                            claim_text=finding,
                            evidence_ids=matching_eids[:1],
                            source_paper_ids=[pid],
                        )
                    )
            elif summary_text:
                parsed_claims.append(
                    ResearchClaim(
                        claim_id=f"C{len(parsed_claims)+1:03d}",
                        claim_text=summary_text[:200],
                        evidence_ids=matching_eids[:1],
                        source_paper_ids=[pid],
                    )
                )

    engine = ResearchIntelligenceEngine()
    result = engine.analyze(
        query=query,
        papers=papers,
        evidence_chunks=parsed_evidence,
        claims=parsed_claims,
    )

    # Add citations count and paper count for legacy compatibility
    result["citations_count"] = len(citations)
    result["summaries"] = summaries

    return result