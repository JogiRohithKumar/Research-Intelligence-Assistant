"""
Report Agent for Research Intelligence Assistant V2 (Stage 4).
Compiles synthesized research, evidence, citations, cross-paper comparisons,
contradiction analysis, evidence strength, and research gap matrix into a structured final report.
"""

from typing import Any, Dict, List, Optional
from app.models.domain import CitationItem, FinalReport


def generate_report(
    query: str,
    summaries: List[Dict[str, Any]],
    citations: List[Dict[str, Any]],
    intelligence: Dict[str, Any],
    claims: Optional[List[Dict[str, Any]]] = None,
    grounded_summary: Optional[str] = None,
    citation_verification: Optional[Dict[str, Any]] = None,
    evidence_registry: Optional[List[Dict[str, Any]]] = None,
    loop_state: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compiles a comprehensive markdown research intelligence report.
    Presents Stage 4 cross-paper intelligence and Stage 5 loop iteration trace alongside Stage 3 evidence grounding.
    """
    verification = intelligence.get("verification", {})
    gaps_data = intelligence.get("gaps", {}) or intelligence.get("legacy_gaps", {})
    consensus_data = intelligence.get("consensus", {})
    strength_data = intelligence.get("evidence_strength", {})
    findings_data = intelligence.get("findings", [])
    comparisons_data = intelligence.get("comparisons", [])
    contradictions_data = intelligence.get("contradictions", [])

    report_lines: List[str] = []

    # Title & Metadata
    report_lines.append("# Academic Research Intelligence Brief\n")
    report_lines.append(f"**Research Query:** {query}\n")

    # 1. Executive Summary & Consensus Synthesis
    report_lines.append("## Executive Summary & Collective Consensus\n")
    if consensus_data and consensus_data.get("synthesis_statement"):
        status = consensus_data.get("consensus_status", "EMERGING")
        report_lines.append(f"**Consensus Status:** {status}\n")
        report_lines.append(f"{consensus_data.get('synthesis_statement')}\n")
        divergent = consensus_data.get("divergent_points", [])
        if divergent:
            report_lines.append("**Divergent Points / Boundary Conditions:**")
            for dp in divergent:
                report_lines.append(f"- {dp}")
            report_lines.append("")
    elif grounded_summary:
        report_lines.append(f"{grounded_summary}\n")
    elif summaries:
        report_lines.append(
            f"This intelligence brief synthesizes findings from **{len(summaries)} peer-reviewed papers** retrieved from scientific literature repositories."
        )
        report_lines.append(f"\n{summaries[0].get('summary', '')}\n")
    else:
        report_lines.append("\nNo literature summaries available.\n")

    # 1.5. Agentic Research Loop Trace (Stage 5)
    if loop_state and loop_state.get("iterations"):
        report_lines.append("## Agentic Research Loop Trace\n")
        stop_reason = loop_state.get("final_stop_reason") or "COMPLETED"
        report_lines.append(f"- **Total Iterations Completed:** {len(loop_state.get('iterations', []))}")
        report_lines.append(f"- **Termination Reason:** `{stop_reason}`")
        report_lines.append(f"- **Cumulative Papers Examined:** {len(loop_state.get('cumulative_paper_ids', []))}")
        report_lines.append(f"- **Cumulative Evidence Chunks:** {len(loop_state.get('cumulative_evidence_ids', []))}\n")
        report_lines.append("| Iteration | Query Used | Papers Added | Claims Supported | Decision | Target Gap |")
        report_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for it in loop_state.get("iterations", []):
            it_id = it.get("iteration_id", 1)
            q = (it.get("query_used", "")[:35]).replace("|", "/")
            new_p = it.get("new_paper_count", 0)
            sup_c = it.get("supported_claims_count", 0)
            dec = it.get("decision", {}).get("action", "STOP_RESEARCH")
            gap = it.get("decision", {}).get("selected_gap")
            gap_str = gap.get("gap_id", "None") if isinstance(gap, dict) else "None"
            report_lines.append(f"| Iteration {it_id} | {q}... | +{new_p} | {sup_c} | `{dec}` | {gap_str} |")
        report_lines.append("")

    # 2. Evidence Strength Assessment (Interpretable, zero fake percentages)
    report_lines.append("## Evidence Strength Assessment\n")
    rating = strength_data.get("rating") or verification.get("evidence_strength", "MODERATE")
    if isinstance(rating, str):
        rating = rating.upper()
    rationale = strength_data.get("rationale") or verification.get("strength_rationale", "Based on retrieved candidate literature.")
    consistency = strength_data.get("consistency_assessment", "Evaluated across retrieved corpus")
    paper_cnt = strength_data.get("supporting_paper_count", len(summaries))
    chunk_cnt = strength_data.get("evidence_chunks_count", len(evidence_registry or []))

    report_lines.append(f"- **Classification:** **{rating}**")
    report_lines.append(f"- **Assessment Rationale:** {rationale}")
    report_lines.append(f"- **Empirical Consistency:** {consistency}")
    report_lines.append(f"- **Literature Base:** {paper_cnt} evaluated papers, {chunk_cnt} verified evidence chunks\n")

    # 3. Cross-Paper Findings (Agreements & Disagreements)
    if findings_data:
        report_lines.append("## Cross-Paper Intelligence Findings\n")
        for f in findings_data:
            fid = f.get("finding_id", "F???")
            ftype = f.get("finding_type", "AGREEMENT")
            text = f.get("finding_text", "")
            eids = f.get("evidence_ids", [])
            eid_str = ", ".join(f"[{e}]" for e in eids) if eids else "General Literature"
            pids = f.get("paper_ids", [])
            pid_str = f" (Papers: {', '.join(pids)})" if pids else ""
            expl = f.get("explanation", "")

            report_lines.append(f"- **[{fid}] ({ftype})** {text}{pid_str} *(Citing: {eid_str})*")
            if expl:
                report_lines.append(f"  *Context:* {expl}")
        report_lines.append("")

    # 4. Contradiction & Discrepancy Analysis
    if contradictions_data:
        report_lines.append("## Contradiction & Discrepancy Analysis\n")
        for ct in contradictions_data:
            cid = ct.get("contradiction_id", "CT???")
            topic = ct.get("topic", "")
            ctype = ct.get("contradiction_type", "METHODOLOGY_DEPENDENT")
            is_genuine = ct.get("is_genuine_contradiction", False)
            ca = ct.get("claim_a", "")
            cb = ct.get("claim_b", "")
            pa = ct.get("paper_a_id", "")
            pb = ct.get("paper_b_id", "")
            explanations = ct.get("possible_explanations", ["UNKNOWN"])

            tag = "Genuine Contradiction" if is_genuine else "Methodological Discrepancy"
            report_lines.append(f"### [{cid}] {topic} ({tag}: {ctype})\n")
            report_lines.append(f"- **Paper {pa}:** {ca}")
            report_lines.append(f"- **Paper {pb}:** {cb}")
            report_lines.append(f"- **Grounded Explanations:** {'; '.join(explanations)}\n")

    # 5. Cross-Paper Study & Methodology Comparison Table
    if comparisons_data:
        report_lines.append("## Study & Methodology Comparison Matrix\n")
        report_lines.append("| Paper ID | Dataset | Method / Architecture | Metrics | Limitations |")
        report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for c in comparisons_data:
            pid = c.get("paper_id", "N/A")
            ds = c.get("dataset") or "Not stated"
            meth = c.get("intervention_or_method") or "Not stated"
            metrics = c.get("metrics") or "Not stated"
            limits = c.get("limitations") or "None stated"
            # Clean pipes to preserve markdown table
            ds_clean = ds.replace("|", "/")
            meth_clean = meth.replace("|", "/")
            metrics_clean = metrics.replace("|", "/")
            limits_clean = limits.replace("|", "/")[:60]
            report_lines.append(f"| {pid} | {ds_clean} | {meth_clean} | {metrics_clean} | {limits_clean} |")
        report_lines.append("")

    # 6. Research Gaps & Open Questions
    report_lines.append("## Research Gaps & Open Questions\n")
    structured_gaps = intelligence.get("gaps", [])
    if isinstance(structured_gaps, list) and structured_gaps and isinstance(structured_gaps[0], dict):
        for g in structured_gaps:
            gid = g.get("gap_id", "G???")
            cat = g.get("category", "EVIDENCE_GAP")
            desc = g.get("description", "")
            affected = g.get("affected_papers", [])
            aff_str = f" *(Affected: {', '.join(affected)})*" if affected else ""
            reasoning = g.get("reasoning", "")
            report_lines.append(f"- **[{gid}] [{cat}]** {desc}{aff_str}")
            if reasoning:
                report_lines.append(f"  *Reasoning:* {reasoning}")
        report_lines.append("")
    else:
        research_gaps = gaps_data.get("research_gaps", [])
        if research_gaps:
            for item in research_gaps:
                report_lines.append(f"- {item}")
            report_lines.append("")

    # 7. Grounded Research Claims (Stage 3 Real RAG)
    if claims:
        report_lines.append("## Verified Grounded Claims\n")
        for c in claims:
            cid = c.get("claim_id", "C???")
            text = c.get("claim_text", "")
            eids = c.get("evidence_ids", [])
            eid_str = ", ".join(f"[{e}]" for e in eids) if eids else "No Evidence Cited"
            status = str(c.get("support_status", "supported")).lower()
            if "claimsupportstatus." in status:
                status = status.replace("claimsupportstatus.", "")

            if status == "supported":
                report_lines.append(f"- **[{cid}]** {text} *(Citing: {eid_str})*")
            elif status == "partially_supported":
                report_lines.append(f"- **[{cid}]** *(Partially Supported)* {text} *(Citing: {eid_str})*")
            else:
                report_lines.append(f"- **[{cid}]** *(Unsupported)* {text}")
        report_lines.append("")

    # 8. Evidence Grounding & Verification Audit
    report_lines.append("## Evidence Grounding & Verification\n")
    if citation_verification:
        g_status = citation_verification.get("grounding_status", "VERIFIED")
        sup = citation_verification.get("supported_claims", 0)
        tot = citation_verification.get("total_claims", 0)
        valid_cits = citation_verification.get("valid_citations", 0)
        report_lines.append(f"- **Grounding Status:** {g_status}")
        report_lines.append(f"- **Verified Grounded Claims:** {sup} / {tot}")
        report_lines.append(f"- **Evidence Citations:** {valid_cits} citations verified against source registry\n")

    prov_audit = intelligence.get("provenance_audit", {})
    if prov_audit:
        chain_intact = prov_audit.get("chain_intact", True)
        promoted = prov_audit.get("promoted_findings_count", len(findings_data))
        total_f = prov_audit.get("total_findings", len(findings_data))
        report_lines.append(f"- **Stage 4 Provenance Chain:** {'INTACT' if chain_intact else 'PARTIALLY_PRUNED'}")
        report_lines.append(f"- **Promoted Research Findings:** {promoted} / {total_f} verified\n")

    # 9. Bibliography
    report_lines.append("## References & Citations\n")
    if citations:
        for i, c in enumerate(citations, 1):
            apa = c.get("apa") or c.get("title", "Untitled")
            report_lines.append(f"{i}. {apa}")
    else:
        report_lines.append("No citations available.")

    return "\n".join(report_lines)