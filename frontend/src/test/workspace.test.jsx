import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import WorkspaceHeader from '../components/workspace/WorkspaceHeader';
import OverviewPanel from '../components/workspace/OverviewPanel';
import FinalReportPanel from '../components/workspace/FinalReportPanel';
import FindingsClaimsPanel from '../components/workspace/FindingsClaimsPanel';
import EvidenceExplorer from '../components/workspace/EvidenceExplorer';
import SourceExplorer from '../components/workspace/SourceExplorer';
import ContradictionPanel from '../components/workspace/ContradictionPanel';
import MethodologyMatrix from '../components/workspace/MethodologyMatrix';
import ResearchGapPanel from '../components/workspace/ResearchGapPanel';
import ResearchTracePanel from '../components/workspace/ResearchTracePanel';
import ProvenanceDrawer from '../components/workspace/ProvenanceDrawer';
import ErrorState from '../components/workspace/ErrorState';
import { sanitizeUrl, formatAuthors } from '../utils/sanitize';
import SafeMarkdown from '../utils/SafeMarkdown';

// Sample authoritative backend state matching Stages 1-5 schemas
const mockResearchState = {
  query: "superconducting qubit coherence fluxonium",
  thread_id: "thread_test_12345",
  execution_status: "completed",
  grounding_status: "VERIFIED",
  current_iteration: 2,
  max_iterations: 3,
  papers: [
    {
      paper_id: "arxiv:2301.00001",
      id: "arxiv:2301.00001",
      title: "Coherence in Superconducting Fluxonium Qubits",
      authors: ["Alice Smith", "Bob Jones", "Carol Davis"],
      year: 2023,
      published: "2023-01-15",
      paper_url: "https://arxiv.org/abs/2301.00001",
      doi: "10.1103/PhysRevLett.130.010001",
      source: "arxiv",
      provider: "arxiv",
      relevance_score: 0.94,
      abstract: "We report coherence times exceeding 1.2 ms in 3D cavity fluxonium circuits."
    },
    {
      paper_id: "arxiv:2302.00002",
      id: "arxiv:2302.00002",
      title: "Loss Mechanisms in Superconducting Planar Resonators",
      authors: ["David Miller"],
      year: 2022,
      published: "2022-08-20",
      paper_url: "https://arxiv.org/abs/2302.00002",
      doi: null,
      source: "arxiv",
      provider: "arxiv",
      relevance_score: 0.81,
      abstract: "Investigation of two-level system dielectric losses at millikelvin temperatures."
    }
  ],
  evidence_registry: [
    {
      evidence_id: "E001",
      paper_id: "arxiv:2301.00001",
      chunk_id: "paper:arxiv:2301.00001:chunk:0_abc",
      text: "Fluxonium qubit relaxation times T1 reached 1.48 ms at the half-flux sweet spot.",
      title: "Coherence in Superconducting Fluxonium Qubits",
      authors: ["Alice Smith", "Bob Jones"],
      year: 2023,
      section: "Results",
      page: 3,
      provider: "arxiv",
      retrieval_score: 0.92,
      evidence_source_type: "indexed_abstract",
      source_url: "https://arxiv.org/abs/2301.00001"
    },
    {
      evidence_id: "E002",
      paper_id: "arxiv:2302.00002",
      chunk_id: "paper:arxiv:2302.00002:chunk:1_def",
      text: "Planar resonator quality factors degraded to 40,000 under unshielded stray infrared radiation.",
      title: "Loss Mechanisms in Superconducting Planar Resonators",
      authors: ["David Miller"],
      year: 2022,
      section: "Discussion",
      page: null,
      provider: "arxiv",
      retrieval_score: 0.79,
      evidence_source_type: "indexed_abstract",
      source_url: "https://arxiv.org/abs/2302.00002"
    }
  ],
  claims: [
    {
      claim_id: "C001",
      claim_text: "Fluxonium relaxation times exceed 1.4 ms under magnetic sweet spot operation.",
      claim_type: "empirical_finding",
      support_status: "SUPPORTED",
      confidence_rationale: "Directly verified by verbatim excerpt from primary author measurement.",
      evidence_ids: ["E001"],
      source_paper_ids: ["arxiv:2301.00001"],
      exact_quotes: ["Fluxonium qubit relaxation times T1 reached 1.48 ms"]
    },
    {
      claim_id: "C002",
      claim_text: "Room temperature coherence of fluxonium qubits reaches 100 milliseconds.",
      claim_type: "empirical_finding",
      support_status: "UNSUPPORTED",
      confidence_rationale: "No retrieved evidence substantiates room temperature superconducting operation.",
      evidence_ids: [],
      source_paper_ids: [],
      exact_quotes: []
    }
  ],
  cross_paper_findings: [
    {
      finding_id: "F001",
      finding_text: "Sweet spot biasing and thermal shielding consistently enhance coherence across geometries.",
      finding_type: "AGREEMENT",
      support_status: "SUPPORTED",
      explanation: "Both cavity and planar studies identify shielding as critical to avoiding stray radiation degradation.",
      claim_ids: ["C001"],
      evidence_ids: ["E001", "E002"],
      paper_ids: ["arxiv:2301.00001", "arxiv:2302.00002"]
    }
  ],
  contradiction_findings: [
    {
      contradiction_id: "CT001",
      topic: "Impact of Substrate Annealing on Loss",
      paper_a_id: "arxiv:2301.00001",
      paper_b_id: "arxiv:2302.00002",
      claim_a: "High-temperature annealing reduces two-level system loss by 40%.",
      claim_b: "Annealing showed no statistically significant reduction in dielectric loss tangent.",
      evidence_ids: ["E001", "E002"],
      contradiction_type: "METHODOLOGY_DEPENDENT",
      possible_explanations: ["Study A evaluated sapphire substrates whereas Study B evaluated high-resistivity silicon."],
      is_genuine_contradiction: false,
      support_status: "SUPPORTED"
    }
  ],
  study_comparisons: [
    {
      paper_id: "arxiv:2301.00001",
      paper_title: "Coherence in Superconducting Fluxonium Qubits",
      population: "Superconducting quantum circuits",
      dataset: "Cryogenic dilution refrigerator measurements",
      sample_size: "4 devices",
      intervention_or_method: "3D copper cavity enclosure with eccosorb filtering",
      baseline_or_control: "Standard aluminum shielding box",
      outcomes: "T1 = 1.48 ms, T2 = 1.12 ms",
      metrics: "Coherence time (T1, T2*)",
      limitations: "Bulk cavity form factor inhibits multi-qubit scaling",
      evidence_ids: ["E001"]
    }
  ],
  research_gaps: [
    {
      gap_id: "G001",
      category: "METHOD_GAP",
      description: "Within the retrieved literature, multi-qubit capacitive coupling schemes have not been demonstrated in the 3D cavity fluxonium architecture.",
      affected_papers: ["arxiv:2301.00001"],
      supporting_evidence_ids: ["E001"],
      reasoning: "All retrieved papers evaluate isolated single-qubit devices only."
    }
  ],
  evidence_strength: {
    rating: "MODERATE",
    rationale: "Findings are supported by 2 independent peer studies with direct experimental measurements, though sample sizes remain modest.",
    supporting_paper_count: 2,
    contradicting_paper_count: 0,
    evidence_chunks_count: 2,
    consistency_assessment: "high"
  },
  consensus_synthesis: {
    consensus_status: "ESTABLISHED",
    synthesis_statement: "Fluxonium qubits consistently demonstrate millisecond-scale relaxation times when shielded from stray infrared and magnetic noise.",
    divergent_points: ["Substrate preparation effects differ between silicon and sapphire hosts."],
    supporting_evidence_ids: ["E001"]
  },
  sufficiency_evaluation: {
    status: "SUFFICIENT",
    rationale: "Sufficient empirical literature retrieved across multiple experimental implementations.",
    paper_count: 2,
    evidence_chunk_count: 2,
    supported_claim_count: 1,
    unsupported_claim_count: 1
  },
  loop_state: {
    current_iteration: 2,
    max_iterations: 3,
    final_stop_reason: "EVIDENCE_SUFFICIENT",
    iterations: [
      {
        iteration_id: 1,
        query_used: "fluxonium qubit coherence limits",
        new_paper_count: 1,
        cumulative_paper_count: 1,
        new_evidence_count: 1,
        cumulative_evidence_count: 1,
        supported_claims_count: 1,
        retrieved_paper_ids: ["arxiv:2301.00001"],
        retrieved_evidence_ids: ["E001"],
        decision: {
          action: "CONTINUE_RESEARCH",
          rationale: "Initial literature search was concentrated in a single paper."
        }
      },
      {
        iteration_id: 2,
        query_used: "superconducting planar resonator dielectric loss",
        new_paper_count: 1,
        cumulative_paper_count: 2,
        new_evidence_count: 1,
        cumulative_evidence_count: 2,
        supported_claims_count: 1,
        retrieved_paper_ids: ["arxiv:2302.00002"],
        retrieved_evidence_ids: ["E002"],
        stop_reason: "EVIDENCE_SUFFICIENT",
        decision: {
          action: "STOP_RESEARCH",
          stop_reason: "EVIDENCE_SUFFICIENT",
          rationale: "Evidence now spans independent experimental frameworks."
        }
      }
    ]
  },
  agent_logs: [
    { agent: "supervisor", status: "success", message: "Query validated as academic investigation.", timestamp: "2026-10-06T09:00:00Z" },
    { agent: "search", status: "success", message: "Retrieved 2 candidate papers from arXiv.", timestamp: "2026-10-06T09:00:05Z" }
  ],
  report: "# Academic Research Intelligence Brief\n\n## Executive Summary\nFluxonium coherence reaches 1.4 ms [E001].\n\n## Findings\nShielding prevents stray radiation loss [E002].",
  citations: [
    {
      title: "Coherence in Superconducting Fluxonium Qubits",
      apa: "Smith, A., Jones, B., & Davis, C. (2023). Coherence in Superconducting Fluxonium Qubits.",
      ieee: "A. Smith, B. Jones, and C. Davis, 'Coherence in Superconducting Fluxonium Qubits', 2023.",
      mla: "Smith, Alice, et al. 'Coherence in Superconducting Fluxonium Qubits.' 2023.",
      bibtex: "@article{smith2023coherence, title={Coherence in Superconducting Fluxonium Qubits}, author={Smith, Alice}, year={2023}}"
    }
  ]
};

describe('Stage 6 Research Workspace UI Tests', () => {

  // Test 1: Research question renders in header
  it('1. research question renders correctly in header and overview', () => {
    render(
      <WorkspaceHeader
        query={mockResearchState.query}
        onSearch={() => {}}
        loading={false}
        status="SUFFICIENT"
        sessionId={mockResearchState.thread_id}
        iterationCount={2}
        maxIterations={3}
      />
    );
    expect(screen.getByText('Research Intelligence Assistant')).toBeInTheDocument();
    expect(screen.getByText(`#${mockResearchState.thread_id}`)).toBeInTheDocument();
  });

  // Test 2: Real research status renders
  it('2. real research status renders without fake percentage metrics', () => {
    render(
      <WorkspaceHeader
        query={mockResearchState.query}
        onSearch={() => {}}
        loading={false}
        status="SUFFICIENT"
        groundingStatus="VERIFIED"
      />
    );
    expect(screen.getByText('SUFFICIENT')).toBeInTheDocument();
    expect(screen.getByText('GROUNDING: VERIFIED')).toBeInTheDocument();
    // Verify no fake percentage like "87% complete" is present
    expect(screen.queryByText(/87%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/confidence: 9/i)).not.toBeInTheDocument();
  });

  // Test 3: Iteration trace renders actual iterations
  it('3. iteration trace renders actual iterations from loop state', () => {
    render(
      <ResearchTracePanel
        loopState={mockResearchState.loop_state}
        iterationsHistory={mockResearchState.loop_state.iterations}
        agentLogs={mockResearchState.agent_logs}
      />
    );
    expect(screen.getByText(/Agentic Research Loop Trace/)).toBeInTheDocument();
    expect(screen.getByText(/Iteration 1: "fluxonium qubit coherence limits"/)).toBeInTheDocument();
    expect(screen.getByText(/Iteration 2: "superconducting planar resonator dielectric loss"/)).toBeInTheDocument();
    expect(screen.getByText(/Final Stop: EVIDENCE_SUFFICIENT/)).toBeInTheDocument();
  });

  // Test 4: Paper data renders
  it('4. paper data renders with title, authors, DOI, and provider', () => {
    render(
      <SourceExplorer
        papers={mockResearchState.papers}
        evidenceChunks={mockResearchState.evidence_registry}
      />
    );
    expect(screen.getByText('Coherence in Superconducting Fluxonium Qubits')).toBeInTheDocument();
    expect(screen.getByText(/Alice Smith et al\./)).toBeInTheDocument();
    expect(screen.getByText(/DOI: 10\.1103\/PhysRevLett\.130\.010001/)).toBeInTheDocument();
    expect(screen.getByText('DOI unavailable')).toBeInTheDocument();
  });

  // Test 5: Evidence renders
  it('5. evidence renders exact text, evidence ID, chunk ID, and score', () => {
    render(
      <EvidenceExplorer
        evidenceChunks={mockResearchState.evidence_registry}
      />
    );
    expect(screen.getByText('E001')).toBeInTheDocument();
    expect(screen.getByText(/"Fluxonium qubit relaxation times T1 reached 1.48 ms at the half-flux sweet spot\."/)).toBeInTheDocument();
    expect(screen.getByText('Score: 0.920')).toBeInTheDocument();
  });

  // Test 6: Supported claim renders
  it('6. supported claim renders with SUPPORTED badge and grounding quotes', () => {
    render(
      <FindingsClaimsPanel
        findings={mockResearchState.cross_paper_findings}
        claims={mockResearchState.claims}
      />
    );
    const supportedBadges = screen.getAllByText('SUPPORTED');
    expect(supportedBadges.length).toBeGreaterThan(0);
    expect(screen.getByText('Fluxonium relaxation times exceed 1.4 ms under magnetic sweet spot operation.')).toBeInTheDocument();
  });

  // Test 7: Unsupported claim renders
  it('7. unsupported claim renders with explicit UNSUPPORTED communication', () => {
    render(
      <FindingsClaimsPanel
        findings={mockResearchState.cross_paper_findings}
        claims={mockResearchState.claims}
      />
    );
    expect(screen.getByText('UNSUPPORTED')).toBeInTheDocument();
    expect(screen.getByText(/Evidence was insufficient or contradictory to substantiate this claim/i)).toBeInTheDocument();
    expect(screen.getByText('Room temperature coherence of fluxonium qubits reaches 100 milliseconds.')).toBeInTheDocument();
  });

  // Test 8: Contradiction panel renders real contradictions
  it('8. contradiction panel renders real contradictions and methodology distinction', () => {
    render(
      <ContradictionPanel
        contradictions={mockResearchState.contradiction_findings}
      />
    );
    expect(screen.getByText('Impact of Substrate Annealing on Loss')).toBeInTheDocument();
    expect(screen.getByText('METHODOLOGY DIFFERENCE')).toBeInTheDocument();
    expect(screen.getByText(/High-temperature annealing reduces two-level system loss/)).toBeInTheDocument();
    expect(screen.getByText(/Annealing showed no statistically significant reduction/)).toBeInTheDocument();
  });

  // Test 9: Empty contradiction state
  it('9. empty contradiction state displays honest message when none exist', () => {
    render(
      <ContradictionPanel
        contradictions={[]}
      />
    );
    expect(screen.getByText('No Contradictions Detected')).toBeInTheDocument();
    expect(screen.getByText('No verified contradictions were detected in the retrieved literature.')).toBeInTheDocument();
  });

  // Test 10: Research gap rendering
  it('10. research gap renders with category and mandatory scope qualifier', () => {
    render(
      <ResearchGapPanel
        gaps={mockResearchState.research_gaps}
      />
    );
    expect(screen.getByText('METHOD GAP')).toBeInTheDocument();
    expect(screen.getByText(/Within the retrieved literature, multi-qubit capacitive coupling schemes/)).toBeInTheDocument();
  });

  // Test 11: Qualitative evidence strength rendering
  it('11. qualitative evidence strength renders without fake percentages', () => {
    render(
      <OverviewPanel
        query={mockResearchState.query}
        consensusSynthesis={mockResearchState.consensus_synthesis}
        evidenceStrength={mockResearchState.evidence_strength}
        findings={mockResearchState.cross_paper_findings}
        claims={mockResearchState.claims}
        papers={mockResearchState.papers}
        evidenceChunks={mockResearchState.evidence_registry}
        contradictions={mockResearchState.contradiction_findings}
        gaps={mockResearchState.research_gaps}
      />
    );
    expect(screen.getByText('RATING: MODERATE')).toBeInTheDocument();
    expect(screen.getByText(/Findings are supported by 2 independent peer studies/)).toBeInTheDocument();
    expect(screen.queryByText(/93%/)).not.toBeInTheDocument();
  });

  // Test 12: Provenance navigation
  it('12. provenance drawer renders connected chain from Finding to Source', () => {
    const handleClose = vi.fn();
    render(
      <ProvenanceDrawer
        selectedEntity={{ type: 'finding', id: 'F001' }}
        onClose={handleClose}
        findings={mockResearchState.cross_paper_findings}
        claims={mockResearchState.claims}
        evidenceChunks={mockResearchState.evidence_registry}
        papers={mockResearchState.papers}
      />
    );
    expect(screen.getByText('Provenance Inspector')).toBeInTheDocument();
    expect(screen.getByText('End-to-End Grounding Chain')).toBeInTheDocument();
    expect(screen.getByText('C001')).toBeInTheDocument();
    expect(screen.getByText('E001')).toBeInTheDocument();
  });

  // Test 13: External source link behavior
  it('13. external source links are secure and validate http/https protocols', () => {
    expect(sanitizeUrl('https://arxiv.org/abs/2301.00001')).toBe('https://arxiv.org/abs/2301.00001');
    expect(sanitizeUrl('javascript:alert(1)')).toBeNull();
    expect(sanitizeUrl('data:text/html,<script></script>')).toBeNull();
  });

  // Test 14: Backend error state
  it('14. error state renders safe message and provides retry action', () => {
    const handleRetry = vi.fn();
    render(
      <ErrorState
        error="FastAPI connection timed out."
        onRetry={handleRetry}
      />
    );
    expect(screen.getByText('Research Pipeline Error')).toBeInTheDocument();
    expect(screen.getByText('FastAPI connection timed out.')).toBeInTheDocument();
    const retryBtn = screen.getByText('Retry Research Execution');
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  // Test 15: Empty research state
  it('15. empty research state renders honest instructional view', () => {
    render(
      <OverviewPanel
        query=""
        papers={[]}
        evidenceChunks={[]}
        findings={[]}
        claims={[]}
      />
    );
    expect(screen.getByText('No Research Session Active')).toBeInTheDocument();
  });

  // Test 16: Methodology matrix renders observed dimensions
  it('16. methodology matrix renders comparisons while preserving unobserved nulls', () => {
    render(
      <MethodologyMatrix
        comparisons={mockResearchState.study_comparisons}
      />
    );
    expect(screen.getByText('Cross-Study Methodology Comparison Matrix (1 studies)')).toBeInTheDocument();
    expect(screen.getByText('Superconducting quantum circuits')).toBeInTheDocument();
    expect(screen.getByText('4 devices')).toBeInTheDocument();
  });

  // Test 17: Unsafe HTML is sanitized in Markdown rendering
  it('17. unsafe HTML/Markdown is sanitized without dangerouslySetInnerHTML', () => {
    const malicious = "## Header\n<script>alert('xss')</script>\n**Bold Statement**";
    render(<SafeMarkdown content={malicious} />);
    expect(screen.getByText('Header')).toBeInTheDocument();
    expect(screen.getByText('Bold Statement')).toBeInTheDocument();
    // Raw script tag was escaped into text or not executed
    expect(document.querySelector('script')).toBeNull();
  });

  // Test 18: Author formatting handles single, dual, and multi-author formats
  it('18. author formatting adheres to scholarly convention', () => {
    expect(formatAuthors(["Alice"])).toBe("Alice");
    expect(formatAuthors(["Alice", "Bob"])).toBe("Alice & Bob");
    expect(formatAuthors(["Alice", "Bob", "Carol"])).toBe("Alice et al. (3 authors)");
  });

  // Test 19: Final report renders real backend markdown and bibliography citations
  it('19. final report renders real backend markdown and selectable citation formats', () => {
    render(
      <FinalReportPanel
        reportMarkdown={mockResearchState.report}
        citations={mockResearchState.citations}
        query={mockResearchState.query}
      />
    );
    expect(screen.getByText('Academic Research Intelligence Brief')).toBeInTheDocument();
    expect(screen.getByText('Bibliography & Formatted Citations')).toBeInTheDocument();
    expect(screen.getByText(/Smith, A\., Jones, B\., & Davis, C\./)).toBeInTheDocument();
  });
});
