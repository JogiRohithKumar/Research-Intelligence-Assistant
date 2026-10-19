# STAGE 5 — AGENTIC RESEARCH LOOP SPECIFICATION

**Project:** Research-Intelligence-Assistant V2  
**Date:** 2026-10-05  
**Stage:** Stage 5 — Agentic Research Loop  
**Status:** COMPLETE & VERIFIED  

---

## 1. Stage 5 Core Objective

Stages 1–4 established a complete single-pass scholarly research pipeline:
1. Candidate search and metadata retrieval
2. Real RAG evidence chunking, embedding, vector storage, and claim-level grounding verification (Stage 3)
3. Deep cross-paper research intelligence with methodology matrices, contradiction detection, explainable evidence strength, and gap detection (Stage 4)

**Stage 5 transforms this linear pipeline into an evidence-driven, bounded agentic research loop.**

The system no longer stops after a single retrieval pass if the evidence base is incomplete, conflicted, or overly narrow. Instead, it systematically interrogates the grounded findings, evaluates whether the evidence is sufficient to answer the user's research question, identifies actionable research gaps, formulates targeted follow-up queries with anti-drift protection, retrieves additional literature, accretes new evidence without overwriting existing provenance, and iterates until the evidence is sufficient or a deterministic safety stop is triggered.

---

## 2. Non-Negotiable Core Invariants & Boundaries

### Literature Boundary Invariant
> **The agentic research loop operates strictly within the boundary of what can be retrieved from real academic search providers and grounded in verifiable evidence chunks.**

1. **Zero Fake Progress:** The system never fabricates additional evidence or pretends that an iteration yielded progress when 0 new papers or 0 new evidence chunks were retrieved.
2. **Zero Fake Confidence:** Sufficiency is never expressed as an arbitrary percentage (e.g. `sufficiency = 87%`). Sufficiency is evaluated as one of five discrete, deterministic qualitative states.
3. **Stage 3 Grounding Gate is Permanent:** Every claim produced in every iteration must pass the exact same Stage 3 semantic support verification pipeline (`ClaimSupportVerifier`). No raw LLM response can enter the state without grounding.
4. **Stage 4 Intelligence Gate is Permanent:** Cross-paper comparisons, contradiction detection, and research gap finding are recomputed over the accreted evidence base.
5. **No Query Drift:** Targeted queries must strictly preserve the parent research intent and retain core topical keywords.
6. **Provenance Chain is Cumulative:** An iteration never overwrites, renumbers, or destroys the evidence or provenance of prior iterations.

---

## 3. End-to-End Pipeline Architecture Flow

```text
                     User Research Question
                               ↓
                        Query Planning
                               ↓
                        Search Engine
                               ↓
                     Candidate Retrieval
                               ↓
                   RAG Evidence Grounding
                   (Registry Accretion)
                               ↓
                   Summary & Citation Pass
                               ↓
                 Research Intelligence (Stage 4)
             (Methodology, Contradictions, Gaps)
                               ↓
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
[Evidence Sufficiency Evaluator]        [Actionable Gap Analyzer]
  - Sufficiency Status                    - Contradiction Gaps
  - Concentration Check                   - Unsupported Claim Gaps
  - Unsupported Claim Check               - Concentration Gaps
  - Contradiction Check                   - Stage 4 Literature Gaps
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                   [ResearchLoopController]
              - Iteration & Budget Enforcement
              - Duplicate Query & Paper Check
              - No-Progress Detection
              - Stopping Rules Evaluation
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
   [Action: STOP_RESEARCH]              [Action: CONTINUE_RESEARCH]
            │                                     │
            │                                     ▼
            │                        [TargetedQueryPlanner]
            │                          - Strategy Selection
            │                          - LLM / Heuristic Generation
            │                          - QueryDriftGuard Verification
            │                                     │
            │                                     ▼
            │                        Targeted Research Query
            │                                     │
            │                        (Loop back to Search)
            │                                     ↺
            ▼
      [Report Agent]
  - Final Academic Brief
  - Agentic Research Loop Trace Table
  - Verified Claims & Intelligence
```

---

## 4. Dedicated Stage 5 Typed Domain Models

Implemented in `app/models/domain.py` and exported through `app/models/__init__.py`:

### A. Qualitative Sufficiency Tiers (`SufficiencyStatus`)
Zero fake percentages. Five deterministic states:
```python
class SufficiencyStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTED = "CONFLICTED"
    NO_RELIABLE_EVIDENCE = "NO_RELIABLE_EVIDENCE"
```

### B. `EvidenceSufficiency`
Structured report documenting the exact empirical basis of the sufficiency determination:
```python
class EvidenceSufficiency(BaseModel):
    status: SufficiencyStatus
    rationale: str
    paper_count: int = 0
    evidence_count: int = 0
    supported_claim_count: int = 0
    unsupported_claim_count: int = 0
    has_unresolved_contradictions: bool = False
    evidence_is_concentrated: bool = False
    primary_paper_id: Optional[str] = None
    subquestions_unanswered: List[str] = Field(default_factory=list)
```

### C. Deterministic Stopping Reasons (`ResearchStopReason`)
```python
class ResearchStopReason(str, Enum):
    EVIDENCE_SUFFICIENT = "EVIDENCE_SUFFICIENT"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    NO_ACTIONABLE_GAPS = "NO_ACTIONABLE_GAPS"
    NO_PROGRESS = "NO_PROGRESS"
    REPEATED_QUERIES = "REPEATED_QUERIES"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    PROVIDER_EXHAUSTION = "PROVIDER_EXHAUSTION"
    MANUAL_STOP = "MANUAL_STOP"
```

### D. Grounded Actionable Gaps (`ActionableResearchGap`)
Every gap is grounded in concrete evidence IDs and affected papers:
```python
class ActionableResearchGap(BaseModel):
    gap_id: str                              # GAP_CT_01, GAP_UNSUP_01, ...
    category: str                            # CONTRADICTION, UNSUPPORTED_CLAIM, CONCENTRATION, GAP
    description: str
    evidence_ids: List[str]                  # Empirical evidence grounding the gap
    affected_papers: List[str]
    severity: str = "MEDIUM"                 # HIGH, MEDIUM, LOW
    recommended_research_action: str
```

### E. Targeted Query Representation (`TargetedResearchQuery`)
```python
class TargetedQueryStrategy(str, Enum):
    POPULATION_FOCUSED = "POPULATION_FOCUSED"
    METHODOLOGY_FOCUSED = "METHODOLOGY_FOCUSED"
    OUTCOME_FOCUSED = "OUTCOME_FOCUSED"
    INTERVENTION_FOCUSED = "INTERVENTION_FOCUSED"
    COMPARISON_FOCUSED = "COMPARISON_FOCUSED"
    CONTRADICTION_FOCUSED = "CONTRADICTION_FOCUSED"
    MISSING_DATASET = "MISSING_DATASET"
    TERMINOLOGY_EXPANSION = "TERMINOLOGY_EXPANSION"
    EVIDENCE_GAP = "EVIDENCE_GAP"

class TargetedResearchQuery(BaseModel):
    parent_query: str
    gap_addressed_id: str
    query_text: str
    strategy: TargetedQueryStrategy
    rationale: str
    target_concepts: List[str]
    iteration_number: int
```

### F. Iteration Audit & Loop State (`ResearchIteration` & `ResearchLoopState`)
```python
class ResearchIteration(BaseModel):
    iteration_id: int
    parent_iteration_id: Optional[int]
    query_used: str
    papers_retrieved_count: int
    new_papers_count: int
    evidence_chunks_count: int
    new_evidence_count: int
    supported_claims_count: int
    unsupported_claims_count: int
    detected_gaps_count: int
    decision: ResearchDecision
    stop_reason: Optional[ResearchStopReason] = None
    elapsed_seconds: float = 0.0

class ResearchLoopState(BaseModel):
    current_iteration: int = 1
    max_iterations: int = 3
    executed_queries: List[str] = Field(default_factory=list)
    executed_gap_ids: List[str] = Field(default_factory=list)
    cumulative_paper_ids: List[str] = Field(default_factory=list)
    cumulative_evidence_ids: List[str] = Field(default_factory=list)
    iterations: List[ResearchIteration] = Field(default_factory=list)
    total_search_calls: int = 0
    consecutive_no_progress_iterations: int = 0
    is_terminal: bool = False
    final_stop_reason: Optional[ResearchStopReason] = None
```

---

## 5. Evidence Sufficiency Evaluation

The `EvidenceSufficiencyEvaluator` (`app/loop/evaluator.py`) evaluates the quality and depth of the current state:

| Condition | Status | Action |
| :--- | :--- | :--- |
| Verified evidence chunks == 0 OR retrieved papers == 0 | `NO_RELIABLE_EVIDENCE` | `CONTINUE_RESEARCH` (or stop if budget exhausted) |
| Active genuine contradictions detected | `CONFLICTED` | `CONTINUE_RESEARCH` (targeted contradiction query) |
| Multiple unsupported claims OR single paper concentration (>75%) | `INSUFFICIENT` | `CONTINUE_RESEARCH` (targeted gap query) |
| Single unsupported claim OR paper count == 1 | `PARTIALLY_SUFFICIENT` | `CONTINUE_RESEARCH` |
| $\ge 2$ independent papers, $\ge 3$ evidence chunks, $\ge 1$ supported claim, 0 unsupported claims, 0 genuine contradictions | `SUFFICIENT` | `STOP_RESEARCH` (`EVIDENCE_SUFFICIENT`) |

Safety stop rules take absolute precedence over sufficiency status:
- If `current_iteration >= max_iterations` $\rightarrow$ `STOP_RESEARCH` (`MAX_ITERATIONS_REACHED`)
- If `consecutive_no_progress >= 1` $\rightarrow$ `STOP_RESEARCH` (`NO_PROGRESS`)
- If `total_search_calls >= max_budget` $\rightarrow$ `STOP_RESEARCH` (`BUDGET_EXHAUSTED`)

---

## 6. Research Gap Identification

The `ActionableGapAnalyzer` (`app/loop/gap_analyzer.py`) scans the existing Stage 3 and Stage 4 states to extract grounded gaps:

1. **Contradiction Gaps (`severity="HIGH"`):**
   Derived directly from Stage 4 `ContradictionFinding` where `is_genuine_contradiction == True`. Points to conflicting papers and specific evidence chunks.
2. **Unsupported Claim Gaps (`severity="HIGH"`):**
   Derived from Stage 3 `ResearchClaim` with status `UNSUPPORTED`. Formulates gaps to verify or refute ungrounded claims.
3. **Evidence Concentration Gaps (`severity="MEDIUM"`):**
   Triggered when over 75% of all evidence chunks originate from a single paper. Generates a gap to locate independent replication or alternative methodologies.
4. **Literature Gaps (`severity="MEDIUM"` / `"LOW"`):**
   Imported from Stage 4 `ResearchGapFinding` (population, dataset, methodology, and generalization gaps).

---

## 7. Targeted Query Reformulation & Anti-Drift Guard

### Strategy-Driven Planning
Queries are generated by `TargetedQueryPlanner` (`app/loop/query_planner.py`) using structured LLM invocation (`gemini-2.5-flash`) with automatic, deterministic heuristic fallback on rate limit or network error.

Each query maps directly to the gap strategy:
- `CONTRADICTION_FOCUSED`: Emphasizes comparative terminology, methodology validation, and conflicting metrics.
- `POPULATION_FOCUSED`: Injects demographic, clinical, or cohort dimensions.
- `METHODOLOGY_FOCUSED`: Targets benchmarks, experimental controls, or algorithmic implementations.
- `MISSING_DATASET`: Targets benchmark corpora or public evaluation sets.

### Query Drift Guard (`QueryDriftGuard`)
To prevent the agent from straying into unrelated research domains:
1. **Keyword Overlap Enforcement:** Extracts topical anchor keywords (excluding stop words) in exact order.
2. **Topical Anchoring:** If a reformulated query drops all core keywords from the parent query, `QueryDriftGuard` rejects it or automatically anchors it by prefixing the parent topic.
3. **Duplicate Query Prevention:** If a reformulated query matches any previously executed query, targeted differentiator tokens are appended.

---

## 8. Loop Control & Hard Safety Limits

Server-side enforced constants configured in `app/core/config.py`:
- `ENABLE_AGENTIC_LOOP`: `True`
- `MAX_RESEARCH_LOOP_ITERATIONS`: `3`
- `MAX_SEARCHES_PER_ITERATION`: `2`
- `MAX_CUMULATIVE_PAPERS`: `20`
- `MAX_CUMULATIVE_EVIDENCE_CHUNKS`: `25`
- `MAX_RESEARCH_BUDGET_CALLS`: `10`

### Termination Conditions
The loop terminates deterministically when:
1. `EVIDENCE_SUFFICIENT`: Multi-study consensus reached with zero unsupported claims.
2. `MAX_ITERATIONS_REACHED`: Configured limit hit (default: 3 iterations).
3. `NO_ACTIONABLE_GAPS`: No grounded gaps remain to investigate.
4. `NO_PROGRESS`: An iteration produces 0 new unique papers and 0 new evidence chunks.
5. `REPEATED_QUERIES`: Reformulation produces duplicate queries that cannot be diversified.
6. `BUDGET_EXHAUSTED`: Maximum allowed provider API calls exceeded.
7. `PROVIDER_EXHAUSTION`: Search provider returned empty results or sustained errors.

---

## 9. Provenance Preservation Across Iterations

In Stage 3, evidence chunks receive stable IDs (`E001`, `E002`, ...). In Stage 5:
1. When `retriever.retrieve_evidence()` is invoked on iteration 2+, it receives `existing_registry`.
2. Existing evidence chunks and their content hashes are preserved.
3. New evidence chunks receive monotonically increasing IDs starting at `registry.count() + 1` (e.g. `E005`, `E006`, etc.).
4. No chunk ID is ever reused, reordered, or overwritten.
5. Every `ResearchFinding` maintains an audit trail back to specific `claim_ids`, which trace to specific `evidence_ids`, which link directly to `paper_id` and chunk text.

---

## 10. LangGraph Pipeline Integration

The LangGraph StateGraph (`app/graph/research_graph.py`) explicitly routes iteration control:

```python
# Graph Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("search", search_node)
workflow.add_node("rag", rag_node)
workflow.add_node("summary", summary_node)
workflow.add_node("citation", citation_node)
workflow.add_node("intelligence", intelligence_node)
workflow.add_node("sufficiency", sufficiency_node)
workflow.add_node("targeted_query", targeted_query_node)
workflow.add_node("report", report_node)

# Conditional Edge from Sufficiency
workflow.add_conditional_edges(
    "sufficiency",
    sufficiency_router,
    {
        "continue": "targeted_query",
        "stop": "report"
    }
)
workflow.add_edge("targeted_query", "search")
```

The router is completely deterministic and prevents hidden recursion or unmonitored cycles.

---

## 11. Loop Observability & Structured Telemetry

Every iteration emits structured logs formatted for security and auditability:
- `session_id`: Unique trace ID
- `iteration`: Current iteration index
- `query`: Executed search string
- `papers`: Total cumulative and newly retrieved counts
- `evidence`: Total cumulative and newly verified chunk counts
- `claims`: `[sup=X, part=Y, unsup=Z]`
- `gaps`: Number of detected actionable gaps
- `action`: `CONTINUE_RESEARCH` vs `STOP_RESEARCH`
- `stop_reason`: Categorical enum reason
- `duration`: Execution time in seconds

*Security Guarantee:* API keys, tokens, session secrets, and credentials are never included in logs or state dumps.

---

## 12. Failure Handling & Graceful Degradation

| Failure Mode | Detection | System Response |
| :--- | :--- | :--- |
| Search Provider Outage | API exception or empty results | Logs warning; checks existing evidence; stops if no progress or synthesizes partial report. Never loops indefinitely. |
| LLM Rate Limit (429) | `RESOURCE_EXHAUSTED` | Gracefully falls back to deterministic heuristic query planner and offline gap analysis. Pipeline never crashes. |
| Malformed LLM Output | Pydantic validation error | Structured validator fails over to regex/keyword heuristic extraction. |
| Query Drift | Keyword loss detected by `QueryDriftGuard` | Replaces drift query with parent-anchored query. |
| Duplicate Retrieval | Paper ID exists in `cumulative_paper_ids` | Filtered out; if 0 new papers found, increments `no_progress` counter and halts loop. |

---

## 13. Security Verification

Preserves the Stage 1 and Stage 2 Security Baselines:
- **No SSRF / Arbitrary Fetching:** Targeted queries are submitted exclusively to configured search providers via internal client abstractions.
- **Server-Side Enforcement:** Iteration count, search budgets, paper limits, and chunk limits are strictly enforced on the server.
- **Input Sanitization:** User research queries and generated targeted queries are sanitized and length-capped.
- **Credential Safety:** Search API keys and LLM keys are held in environment variables and never logged or reflected to the frontend.

---

## 14. Verification & Testing

Stage 5 is covered by 16 targeted tests in `tests/test_stage5_agentic_loop.py` plus the complete regression suite across Stages 1–4:

1. `test_sufficient_evidence_stops_loop`: Verified stop when evidence is multi-study and consistent.
2. `test_insufficient_evidence_triggers_targeted_search`: Verified loop continuation when claims lack support.
3. `test_targeted_query_addresses_correct_gap`: Verified query formulation tailored to specific gap category.
4. `test_query_drift_guard_preserves_anchor_terms`: Verified that drift guard enforces parent query keywords.
5. `test_duplicate_query_detection_and_differentiation`: Verified differentiation when query matches history.
6. `test_repeated_gap_detection`: Verified prevention of infinite loops on intractable gaps.
7. `test_no_progress_stops_loop`: Verified termination when iteration yields 0 new papers and 0 new chunks.
8. `test_max_iteration_limit`: Verified strict stop when iteration == `max_iterations`.
9. `test_research_budget_limit`: Verified strict stop when total search calls exceed budget.
10. `test_duplicate_papers_do_not_inflate_progress`: Verified filtering of duplicate paper IDs.
11. `test_evidence_accretion_sequential_ids`: Verified seamless accretion with non-colliding IDs (`E001` -> `E005`).
12. `test_provenance_survives_multiple_iterations`: Verified complete chain across iterations.
13. `test_provider_failure_does_not_loop_forever`: Verified graceful exit on provider exhaustion.
14. `test_contradiction_conflict_triggers_conflicted_state`: Verified detection and targeted follow-up.
15. `test_llm_structured_output_failure_handled_gracefully`: Verified fallback to heuristic planner.
16. `test_end_to_end_langgraph_pipeline_stage5`: Full multi-node pipeline execution with iterative trace generation.

**All Stage 5 tests pass cleanly.**
