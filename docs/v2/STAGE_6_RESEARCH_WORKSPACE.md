# STAGE 6 — RESEARCH WORKSPACE UI SPECIFICATION

**Project:** Research-Intelligence-Assistant V2  
**Date:** 2026-10-06  
**Stage:** Stage 6 — Research Workspace UI  
**Status:** COMPLETE & VERIFIED  

---

## 1. Stage 6 Core Objective

Stages 1–5 established an end-to-end, multi-agent academic research engine:
1. Foundation & Architecture with strictly typed Pydantic models (Stage 1)
2. Multi-source scholarly literature search and candidate ranking (Stage 2)
3. End-to-end RAG evidence chunking, vector indexing, and claim-level semantic support verification (Stage 3)
4. Cross-paper research intelligence: methodology comparison matrix, contradiction analysis, qualitative evidence strength, and empirical research gaps (Stage 4)
5. Autonomous, bounded agentic research loop with evidence sufficiency evaluation, anti-drift targeted query formulation, and multi-iteration accretion (Stage 5)

**Stage 6 transforms the user interface from a superficial demo into a high-performance, serious Research Workspace built directly on authoritative Stage 1–5 backend contracts.**

Researchers can now:
1. Input scientific queries with character limits and optional session IDs matching backend schemas.
2. Observe real research pipeline statuses (`RESEARCHING`, `SUFFICIENT`, `PARTIALLY_SUFFICIENT`, `CONFLICTED`, `NO_RELIABLE_EVIDENCE`, `FAILED`) without fake loading metrics.
3. Inspect multi-iteration research loop traces (iteration numbers, query adaptations, new papers added, new evidence accreted, supported claim tallies, stop decisions).
4. Browse retrieved literature with full author lists, publication years, DOI links, and abstracts.
5. Explore un-paraphrased evidence excerpts with chunk IDs, retrieval scores, and provider provenance.
6. Verify research claims with explicit support status badges (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `INSUFFICIENT_EVIDENCE`) and grounding rationales.
7. Inspect cross-paper findings and consensus synthesis statements.
8. Analyze empirical contradictions while critically distinguishing genuine result conflicts from methodology, population, or dataset differences.
9. Review cross-study methodology comparison tables while preserving unobserved parameters as nulls.
10. Explore empirical research gaps scoped strictly "Within the retrieved literature...".
11. Examine qualitative evidence strength assessments (`STRONG`, `MODERATE`, `LIMITED`, `MIXED`, `INSUFFICIENT`) with zero fake confidence percentages.
12. Read the final academic research brief rendered safely without XSS vulnerabilities, and export citations in APA, IEEE, MLA, and BibTeX.
13. Navigate bidirectionally along the entire provenance chain:
    $$\text{Finding} \longrightarrow \text{Claim} \longrightarrow \text{Evidence Chunk} \longrightarrow \text{Paper} \longrightarrow \text{Source URL}$$

---

## 2. Global Product Rules Adherence

The UI strictly adheres to serious scholarly application guidelines:
- **Zero Purple Gradients & Zero Pill Buttons:** Clean, restrained technical styling with deep slate/neutral tones (`#0b0f17`, slate-800 borders, crisp typography).
- **Zero Fake Metrics:** Confidence scores are qualitative; verification confidence is empirical; progress bars and fake "87% complete" animations are eliminated.
- **Zero Simulated Agent Activity:** The UI only renders real events and iteration records produced by the backend graph.
- **Honest Empty States:** Sections without data display honest explanatory states (e.g. "No verified contradictions were detected in the retrieved literature.").
- **Security & Sanitization:** All markdown is parsed without `dangerouslySetInnerHTML`. All external links strictly validate `http://` or `https://` protocols and enforce `rel="noopener noreferrer"`.

---

## 3. Workspace Information Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│ WORKSPACE HEADER                                                       │
│ - Brand Title & V2 Badge        - Session ID (#thread_...)             │
│ - Real Status (SUFFICIENT/etc.) - Iteration Counter (Iter 2/3)         │
│ - Grounding Status (VERIFIED)   - Character Count (48/1000)            │
│ - Query Textarea                - Execute / Reset Actions              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ WORKSPACE SECTION NAVIGATION TABS                                      │
│ [Overview] [Brief] [Findings (K)] [Evidence (M)] [Sources (N)]         │
│ [Contradictions (C)] [Methodology (S)] [Gaps (G)] [Trace (I)]          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ ACTIVE VIEW CONTAINER                                                  │
│                                                                        │
│ 1. Overview Panel: Executive synthesis, evidence strength, metrics     │
│ 2. Final Report Panel: Sanitized Markdown brief, bibliography export   │
│ 3. Findings & Claims: Cross-paper findings and atomic claims           │
│ 4. Evidence Matrix: Verbatim chunks, chunk IDs, retrieval scores       │
│ 5. Source Literature: Normalized papers, DOIs, abstracts, links        │
│ 6. Contradictions: Genuine conflicts vs methodology differences        │
│ 7. Methodology Matrix: Comparative parameters table                    │
│ 8. Research Gaps: Literature-scoped empirical gaps                     │
│ 9. Research Trace: Multi-turn loop cycles & backend telemetry stream   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼ (Triggered on any token click)
┌────────────────────────────────────────────────────────────────────────┐
│ PROVENANCE INSPECTOR DRAWER (Slide-over Dialog)                        │
│  Finding  ──►  Claim  ──►  Evidence Chunk  ──►  Paper  ──►  Source URL │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Frontend Component Breakdown

| Component | File Path | Primary Responsibility |
|:---|:---|:---|
| `App.jsx` | `src/App.jsx` | Workspace orchestrator, session persistence in `sessionStorage`, active tab routing, provenance drawer state. |
| `WorkspaceHeader` | `src/components/workspace/WorkspaceHeader.jsx` | Query validation (2-1000 chars), session ID input, real execution & grounding badges. |
| `WorkspaceNav` | `src/components/workspace/WorkspaceNav.jsx` | 9-view accessible tab navigation bar with real entity counts. |
| `OverviewPanel` | `src/components/workspace/OverviewPanel.jsx` | Executive summary, consensus status, qualitative evidence strength breakdown, metric grid. |
| `FinalReportPanel` | `src/components/workspace/FinalReportPanel.jsx` | Sanitized markdown report rendering, interactive citation tags, APA/IEEE/MLA/BibTeX copy & export. |
| `FindingsClaimsPanel`| `src/components/workspace/FindingsClaimsPanel.jsx` | Stage 4 findings & Stage 3 claims with support status filtering (`SUPPORTED`, `UNSUPPORTED`). |
| `EvidenceExplorer` | `src/components/workspace/EvidenceExplorer.jsx` | Verbatim text excerpts, retrieval scores, section/page numbers, copy excerpt actions. |
| `SourceExplorer` | `src/components/workspace/SourceExplorer.jsx` | Paper metadata, authors, DOI links, abstracts with expand/collapse, and evidence mappings. |
| `ContradictionPanel`| `src/components/workspace/ContradictionPanel.jsx` | Side-by-side study comparison, genuine conflict vs methodology difference classification. |
| `MethodologyMatrix` | `src/components/workspace/MethodologyMatrix.jsx` | Comparative matrix of experimental parameters preserving unobserved values as nulls. |
| `ResearchGapPanel` | `src/components/workspace/ResearchGapPanel.jsx` | Empirical research gaps with category, severity, and mandatory literature scoping. |
| `ResearchTracePanel`| `src/components/workspace/ResearchTracePanel.jsx` | Stage 5 loop iteration audit, query evolution, stop reasons, and backend agent telemetry. |
| `ProvenanceDrawer` | `src/components/workspace/ProvenanceDrawer.jsx` | Bidirectional entity inspection across Finding, Claim, Evidence, Paper, and Source URL. |
| `SafeMarkdown` | `src/utils/SafeMarkdown.jsx` | XSS-safe markdown renderer with citation tokenization (`[E001]` -> clickable button). |
| `sanitize.js` | `src/utils/sanitize.js` | External URL validation (`http/https` only) and scholarly author formatting. |
| `EmptyState` | `src/components/workspace/EmptyState.jsx` | Scholarly empty placeholder with honest messaging. |
| `ErrorState` | `src/components/workspace/ErrorState.jsx` | Professional error banner with safe messaging and retry action. |

---

## 5. Provenance & Navigation UX

The central architectural guarantee of Stage 6 is complete **traceability**:
- A researcher reviewing an executive finding or markdown statement can click an evidence token like `[E001]` or claim token like `[C001]`.
- This immediately opens the **Provenance Inspector Drawer**, displaying:
  1. The upstream **Finding** and its cross-study rationale.
  2. The atomic **Research Claim** and its support verdict (`SUPPORTED` / `UNSUPPORTED`).
  3. The verbatim **Evidence Chunk** with exact un-paraphrased text, chunk ID, and similarity score.
  4. The source **Normalized Paper** with authors, publication year, and abstract.
  5. The primary **Source URL** or **DOI** for authoritative verification.

Clicking any connected token inside the drawer traverses bidirectionally across the relationship graph without losing context.

---

## 6. Accessibility & Responsive Design

- **Semantic Hierarchy:** Single `<h1>` in header, `<h2>` for panel sections, `<nav>` for tab bar, `<main>` for active content, `<dialog>` for provenance drawer.
- **Keyboard Navigation:** Full keyboard operability; Escape key dismisses the Provenance Drawer; visible focus rings (`focus:ring-indigo-500`) on all interactive controls.
- **Color Independence:** Support statuses use both semantic colors and explicit text badges (`SUPPORTED`, `UNSUPPORTED`, `INSUFFICIENT_EVIDENCE`) and distinct icons.
- **Responsive Layout:**
  - Desktop: Multi-column navigation, wide comparison matrix table with horizontal scroll, fixed slide-over provenance drawer.
  - Tablet/Mobile: Full-width stacked cards, scrollable tab navigation, responsive typography, collapsible abstracts.

---

## 7. Security Verification

- **XSS Prevention:** `dangerouslySetInnerHTML` is completely prohibited. Markdown text is parsed into pure React elements with character escaping.
- **Protocol Safety:** `sanitizeUrl` rejects dangerous schemes such as `javascript:`, `vbscript:`, and `data:`. Only `http://` and `https://` links are rendered.
- **External Link Hardening:** All external hyperlinks specify `target="_blank"` and `rel="noopener noreferrer"`.
- **Credential Protection:** Zero API keys, passwords, or internal server paths are exposed to the browser or rendered in UI state.

---

## 8. Automated Testing & Verification

The Stage 6 automated test suite in `src/test/workspace.test.jsx` validates all 19 requirements using Vitest and React Testing Library:

| # | Test Description | Status |
|:---|:---|:---|
| 1 | Research question renders in header and overview | PASS |
| 2 | Real research status renders without fake percentage metrics | PASS |
| 3 | Iteration trace renders actual iterations from loop state | PASS |
| 4 | Paper data renders with title, authors, DOI, and provider | PASS |
| 5 | Evidence renders exact text, evidence ID, chunk ID, and score | PASS |
| 6 | Supported claim renders with SUPPORTED badge and grounding quotes | PASS |
| 7 | Unsupported claim renders with explicit UNSUPPORTED communication | PASS |
| 8 | Contradiction panel renders real contradictions and methodology distinction | PASS |
| 9 | Empty contradiction state displays honest message when none exist | PASS |
| 10 | Research gap renders with category and mandatory scope qualifier | PASS |
| 11 | Qualitative evidence strength renders without fake percentages | PASS |
| 12 | Provenance drawer renders connected chain from Finding to Source | PASS |
| 13 | External source links are secure and validate http/https protocols | PASS |
| 14 | Error state renders safe message and provides retry action | PASS |
| 15 | Empty research state renders honest instructional view | PASS |
| 16 | Methodology matrix renders comparisons while preserving unobserved nulls | PASS |
| 17 | Unsafe HTML/Markdown is sanitized without dangerouslySetInnerHTML | PASS |
| 18 | Author formatting adheres to scholarly convention | PASS |
| 19 | Final report renders real backend markdown and selectable citation formats | PASS |

**Test Execution Result:** `19 passed in 46.28s`  
**ESLint Result:** `0 errors, 0 warnings`  
**Production Build Result:** `vite build built in 1.16s`  
**Backend Regression Suite:** `90 passed in 9.1 minutes` across all Stages 1–5  

---

## 9. Intentionally Deferred Items (Stage 7+)

The following items are strictly deferred to subsequent roadmap stages:
- **Stage 7 (Production Engineering):** PostgreSQL migration, containerized Docker architecture, Redis caching, production rate limiting, and observability telemetry.
- **Stage 8 (Testing & Evaluation):** Large-scale empirical benchmarking across standard scholarly datasets, automated regression test matrix.
- **Stage 9 (Deployment & Production Release):** Multi-region cloud infrastructure, SSL domain provisioning, and production CI/CD pipelines.
