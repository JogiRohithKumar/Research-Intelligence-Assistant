# STAGE 4 — RESEARCH INTELLIGENCE SPECIFICATION

**Project:** Research-Intelligence-Assistant V2  
**Date:** 2026-10-05  
**Stage:** Stage 4 — Research Intelligence  
**Status:** COMPLETE & VERIFIED  

---

## 1. Stage 4 Core Objective

Stage 3 established grounded RAG where factual statements are constrained to verifiable evidence chunks (`EvidenceChunk`) and verified claims (`ResearchClaim`).

**Stage 4 elevates the system into a genuine scholarly research intelligence platform**:
It transforms the system from:
> *"Here are papers and grounded claims."*

into:
> *"Here is what the retrieved evidence collectively says, where studies agree, where they disagree, why they may disagree, how their methodologies differ, where evidence is strong or weak, and what research gaps remain."*

---

## 2. Non-Negotiable Core Architectural Invariant

### EVIDENCE MUST REMAIN THE SOURCE OF TRUTH
Stage 4 strictly inherits the non-negotiable Stage 3 invariant:

> **No research intelligence is allowed to outrun the evidence layer.**

```text
No evidence
    ↓
No research intelligence (INSUFFICIENT)

Weak / Single-study evidence
    ↓
Weak / qualified intelligence (LIMITED)

Conflicting evidence
    ↓
Explicit disagreement / uncertainty (MIXED)

Strong consistent evidence
    ↓
Stronger multi-study synthesis (STRONG / MODERATE)
```

The system strictly prohibits an LLM or heuristic from fabricating:
- Artificial consensus or unanimity
- Substantive contradictions when differences stem merely from datasets, tasks, or metrics
- Unobserved research gaps or speculation
- Methodology details (randomization, sample size, baselines, clinical quality) not stated in the evidence
- Causal explanations or superiority claims
- Fake numerical confidence scores (e.g. `confidence = 97%` or `0.85`)

---

## 3. End-to-End Pipeline Architecture Flow

```text
┌────────────────────────────────────────────────────────┐
│               Stage 3: Evidence Layer                  │
│  Candidate Papers -> ChromaDB -> EvidenceRegistry     │
│  -> Grounded Claims -> ClaimSupportVerifier            │
└───────────────────────────┬────────────────────────────┘
                            │ Validated Claims & EvidenceChunks
                            ▼
┌────────────────────────────────────────────────────────┐
│             Stage 4: Research Intelligence             │
│                                                        │
│  1. MethodologyComparator                             │
│     Extracts dataset, method, baseline, metrics,       │
│     limitations; preserves None for unstated fields.   │
│                            │                           │
│                            ▼                           │
│  2. ContradictionDetector                             │
│     Distinguishes genuine conflicts from differences  │
│     in datasets, populations, or methodologies.       │
│                            │                           │
│                            ▼                           │
│  3. CrossPaperAnalyzer                                 │
│     Identifies grounded AGREEMENT and DISAGREEMENT;   │
│     rejects ungrounded "all studies agree" assertions. │
│                            │                           │
│                            ▼                           │
│  4. EvidenceStrengthEvaluator                         │
│     Computes explainable ratings: STRONG, MODERATE,    │
│     LIMITED, MIXED, INSUFFICIENT (zero fake %).        │
│                            │                           │
│                            ▼                           │
│  5. ResearchGapDetector                               │
│     Derives gaps from evidence patterns & limitations; │
│     enforces "Within the retrieved literature..."     │
│                            │                           │
│                            ▼                           │
│  6. ConsensusSynthesizer                              │
│     Generates grounded narrative synthesis; handles    │
│     insufficient evidence & mixed findings honestly.   │
│                            │                           │
│                            ▼                           │
│  7. ProvenanceGuard & Audit                           │
│     Purges any finding citing hallucinated IDs;        │
│     verifies chain: Finding -> Claim -> Evidence.      │
└───────────────────────────┬────────────────────────────┘
                            │ Verified Intelligence Package
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Report Node                          │
│  Compiles Academic Brief with Methodology Matrix,      │
│  Contradiction Analysis, Evidence Strength, & Gaps     │
└────────────────────────────────────────────────────────┘
```

---

## 4. Dedicated Research Intelligence Domain Models

Implemented in `app/models/domain.py`:

### A. `ResearchFinding`
Represents an evidence-grounded cross-paper finding.
```python
class FindingType(str, Enum):
    AGREEMENT = "AGREEMENT"
    DISAGREEMENT = "DISAGREEMENT"
    CONTRADICTION = "CONTRADICTION"
    METHODOLOGY_DIFFERENCE = "METHODOLOGY_DIFFERENCE"
    EVIDENCE_GAP = "EVIDENCE_GAP"
    CONSENSUS = "CONSENSUS"
    QUALIFIED_CONCLUSION = "QUALIFIED_CONCLUSION"

class ResearchFinding(BaseModel):
    finding_id: str                          # F001, F002, ...
    finding_text: str                        # Factual finding proposition
    finding_type: FindingType                # Classification
    claim_ids: List[str]                     # Referenced Stage 3 claims (e.g. ['C001'])
    evidence_ids: List[str]                  # Referenced evidence chunk IDs (e.g. ['E001'])
    paper_ids: List[str]                     # Associated source paper IDs
    support_status: ClaimSupportStatus       # SUPPORTED
    explanation: str                         # Factual context
```

### B. `PaperComparison`
Represents structured methodology comparison across observed dimensions:
```python
class PaperComparison(BaseModel):
    paper_id: str
    paper_title: str
    research_question: Optional[str] = None
    population: Optional[str] = None
    dataset: Optional[str] = None
    sample_size: Optional[str] = None
    intervention_or_method: Optional[str] = None
    baseline_or_control: Optional[str] = None
    outcomes: Optional[str] = None
    metrics: Optional[str] = None
    evaluation_method: Optional[str] = None
    limitations: Optional[str] = None
    evidence_ids: List[str]                  # Supporting evidence IDs
```
*Rule:* Every populated field must have evidence provenance. Absent fields are strictly `None`.

### C. `ContradictionFinding`
Represents substantive conflicts vs methodological differences:
```python
class ContradictionType(str, Enum):
    DIRECT_RESULT_CONFLICT = "DIRECT_RESULT_CONFLICT"
    DIRECTIONAL_CONFLICT = "DIRECTIONAL_CONFLICT"
    POPULATION_CONFLICT = "POPULATION_CONFLICT"
    METHODOLOGY_DEPENDENT = "METHODOLOGY_DEPENDENT"
    OUTCOME_DEFINITION_DIFFERENCE = "OUTCOME_DEFINITION_DIFFERENCE"
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_A_CONTRADICTION = "NOT_A_CONTRADICTION"

class ContradictionFinding(BaseModel):
    contradiction_id: str                    # CT001, CT002, ...
    topic: str
    paper_a_id: str
    paper_b_id: str
    claim_a: str
    claim_b: str
    evidence_ids: List[str]
    contradiction_type: ContradictionType
    possible_explanations: List[str]        # Evidence-supported or ["UNKNOWN"]
    is_genuine_contradiction: bool           # True ONLY for incompatible findings
    support_status: ClaimSupportStatus
```

### D. `EvidenceStrength`
Interpretable rating without fake percentages:
```python
class EvidenceStrengthRating(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"
    MIXED = "MIXED"
    INSUFFICIENT = "INSUFFICIENT"

class EvidenceStrength(BaseModel):
    rating: EvidenceStrengthRating
    rationale: str
    supporting_paper_count: int = 0
    contradicting_paper_count: int = 0
    evidence_chunks_count: int = 0
    consistency_assessment: str = ""
```

### E. `ResearchGapFinding`
Grounded gaps derived from empirical patterns:
```python
class ResearchGapCategory(str, Enum):
    POPULATION_GAP = "POPULATION_GAP"
    DATASET_GAP = "DATASET_GAP"
    METHOD_GAP = "METHOD_GAP"
    OUTCOME_GAP = "OUTCOME_GAP"
    TIME_HORIZON_GAP = "TIME_HORIZON_GAP"
    COMPARISON_GAP = "COMPARISON_GAP"
    GENERALIZATION_GAP = "GENERALIZATION_GAP"
    EVIDENCE_GAP = "EVIDENCE_GAP"

class ResearchGapFinding(BaseModel):
    gap_id: str                              # G001, G002, ...
    category: ResearchGapCategory
    description: str                         # Prefixed with "Within the retrieved literature..."
    affected_papers: List[str]
    supporting_evidence_ids: List[str]
    reasoning: str
```

### F. `ConsensusSynthesis`
```python
class ConsensusSynthesis(BaseModel):
    consensus_status: str                    # ESTABLISHED, EMERGING, MIXED, INSUFFICIENT_EVIDENCE
    synthesis_statement: str
    divergent_points: List[str]
    evidence_strength: EvidenceStrength
    supporting_evidence_ids: List[str]
```

---

## 5. Distinguishing Difference from Contradiction

A critical flaw in naive AI research tools is confusing differing results with genuine contradictions:
- **Scenario 1:** Paper A reports 91% accuracy on Dataset X. Paper B reports 87% accuracy on Dataset Y.
  - *Naive LLM:* "Contradiction! Paper A contradicts Paper B on accuracy."
  - *Stage 4 System:* **NOT A CONTRADICTION**. Different datasets explain differing numeric outcomes. Classified as `METHODOLOGY_DEPENDENT` with `is_genuine_contradiction = False`.
- **Scenario 2:** Paper A reports that Method X improves throughput on a given benchmark. Paper B reports that Method X degrades throughput or yields no significant improvement under comparable conditions.
  - *Stage 4 System:* **GENUINE CONTRADICTION**. Classified as `DIRECT_RESULT_CONFLICT` with `is_genuine_contradiction = True`.
- **Explanation Rule:** If the papers do not document why they differ, `possible_explanations` defaults strictly to `["UNKNOWN"]`. Fabricating causal hypotheses is prohibited.

---

## 6. Interpretable Evidence Strength vs Fake Metrics

Stage 4 strictly forbids fake percentages (e.g. `confidence = 94%`, `0.75 confidence score`, `85% consensus`).
Instead, `EvidenceStrengthEvaluator` computes an interpretable classification:
- **`INSUFFICIENT`**: 0 papers or 0 evidence chunks. Rationale explicitly cites inadequate literature.
- **`MIXED`**: Genuine result conflicts detected across studies under comparable conditions.
- **`LIMITED`**: Single-study finding (unreplicated) or multi-study with severe methodological fragmentation.
- **`MODERATE`**: 2–3 independent studies reporting concordant directional findings.
- **`STRONG`**: 4+ independent studies demonstrating multi-team convergence without conflicts.

Every rating is paired with a factual, verifiable `rationale` detailing the paper count and consistency.

---

## 7. Evidence-Grounded Research Gaps

Research gaps are derived strictly from evidence distributions:
- **`DATASET_GAP`**: When all retrieved studies evaluate exclusively on a single corpus or benchmark.
- **`GENERALIZATION_GAP`**: Direct author-stated limitations documented in study excerpts.
- **`COMPARISON_GAP`**: Absence of explicit baseline comparisons against alternative models.
- **`POPULATION_GAP`**: Evidence concentrated on one model scale or demographic while others remain unstudied.
- **Scope Guard:** Every gap description begins with: `"Within the retrieved literature, ..."` to ensure no false global completeness is asserted.

---

## 8. Provenance Guard & Anti-Slop Rejection

Implemented in `app/intelligence/provenance_guard.py`:
1. **Chain Verification:**
   $$\text{ResearchFinding} \longrightarrow \text{claim\_ids} \longrightarrow \text{evidence\_ids} \longrightarrow \text{paper\_id} \longrightarrow \text{chunk\_id} \longrightarrow \text{text}$$
2. **Hallucination Hard Rejection:** If an LLM or finding cites a phantom evidence ID (e.g. `E999`), `ProvenanceGuard` immediately purges the finding from promotion into the final report.
3. **Adversarial Qualification:** If an input or LLM asserts `"All studies agree"` while the contradiction detector identified genuine divergence, the finding is demoted to `QUALIFIED_CONCLUSION` and modified to highlight study differences.

---

## 9. LangGraph Pipeline Integration

Stage 4 seamlessly upgrades `intelligence_node` and `report_node` within the authoritative LangGraph state graph (`app/graph/research_graph.py`):
```text
supervisor -> search -> rag -> summary -> citation -> intelligence -> report -> END
```
- `intelligence_node` receives `papers`, `evidence_registry`, `claims`, `summaries`, `citations`.
- Populates state keys:
  - `cross_paper_findings`
  - `study_comparisons`
  - `contradiction_findings`
  - `evidence_strength`
  - `research_gaps`
  - `consensus_synthesis`
  - `verification` (legacy compatibility)
  - `gaps` (legacy compatibility)
- `report_node` formats all sections into a comprehensive academic brief.

---

## 10. Limitations & Honest Disclosures

1. **Abstract-Level Evidence:** Search providers currently retrieve titles, abstracts, and metadata snippets. Full-text PDF table and figure extraction is deferred.
2. **Zero Inferred Methodology:** If an abstract omits sample size or baseline, it remains `None`. The system does not attempt to guess missing details.
3. **Corpus Boundary:** Contradictions and gaps are relative to the *retrieved literature*, not the entire universe of scientific papers.

---

## 11. Testing & Empirical Validation

Comprehensive automated test suite executed in `tests/test_stage4_intelligence.py` (16 tests) + full test suite (74 tests):
```bash
.\.venv-2\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

### Critical Stage 4 Tests:
1. `test_cross_paper_agreement`: Validates concordant directional findings produce `AGREEMENT`.
2. `test_false_contradiction_rejected`: Validates differing datasets do not trigger genuine contradiction (`NOT_A_CONTRADICTION`).
3. `test_genuine_contradiction_detected`: Validates incompatible outcomes under same method trigger `DIRECT_RESULT_CONFLICT`.
4. `test_methodology_difference_not_direct_conflict`: Validates different methods produce `METHODOLOGY_DEPENDENT`.
5. `test_research_gap_detection`: Validates categorized gap with mandatory `"Within the retrieved literature"` prefix.
6. `test_insufficient_evidence_no_fake_consensus`: Validates sparse evidence produces `INSUFFICIENT` and honest consensus statement.
7. `test_evidence_strength_classification`: Validates `MIXED`, `LIMITED`, `MODERATE`, and `STRONG` ratings.
8. `test_adversarial_unsupported_consensus_rejected`: Rejects "All studies agree" when contradictions exist.
9. `test_provenance_verification_purges_hallucinated_ids`: Prunes findings citing phantom `E999`.
10. `test_end_to_end_research_intelligence_engine`: Validates engine output schema and zero fake confidence metrics.
11. `test_llm_cross_paper_analysis_mocked`: Validates structured LLM cross-paper parser.
12. `test_llm_contradiction_detection_mocked`: Validates structured LLM contradiction parser.
13. `test_llm_research_gap_detection_mocked`: Validates structured LLM gap parser.
14. `test_llm_methodology_extraction_mocked`: Validates structured LLM methodology extractor.
15. `test_llm_consensus_synthesis_mocked`: Validates structured LLM consensus synthesis.
16. `test_full_langgraph_stage4_pipeline_execution`: Full end-to-end execution of `research_graph`.

---

## 12. Stage 5 Boundary Definition

Stage 4 is strictly an analytical engine operating on retrieved evidence. The following capabilities are reserved for **Stage 5 — Agentic Research Loop**:
- Autonomous multi-turn research iterations
- Automatic follow-up sub-query generation based on detected gaps
- Dynamic retrieval expansion loops
- Termination criteria and loop guards
- Human-in-the-loop (HITL) pause/resume checkpoints
