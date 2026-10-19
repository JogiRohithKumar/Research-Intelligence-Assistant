# V2 SYSTEM ARCHITECTURE DOCUMENTATION
**Project:** Research-Intelligence-Assistant V2  
**Date:** 2026-10-19  
**Stage:** Stage 9 — Deployment & Production Release  
**Status:** STAGE 9 DEPLOYMENT & PRODUCTION RELEASE OPERATIONAL & VERIFIED  

---

## 1. System Overview

**Research-Intelligence-Assistant V2** is an enterprise-grade academic research intelligence platform. It autonomously parses complex research queries, retrieves scientific literature across multiple scholarly repositories, extracts grounded evidence with sentence-level citations, performs cross-paper methodology comparison, detects consensus and contradictions across peer-reviewed studies, maps unaddressed research gaps, evaluates evidence sufficiency, iteratively executes targeted gap-driven research cycles with anti-drift protection, and synthesizes an academic intelligence brief.

The system is engineered around a **strict 9-stage locked roadmap**:
1. Foundation & Architecture — COMPLETE
2. Research Search & Retrieval Engine — COMPLETE
3. Real RAG & Evidence Grounding — COMPLETE
4. Research Intelligence — COMPLETE
5. Agentic Research Loop — COMPLETE
6. Research Workspace UI — COMPLETE
7. Production Engineering — COMPLETE
8. Testing & Evaluation — COMPLETE
9. Deployment & Production Release — COMPLETE & VERIFIED

```
┌────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                            │
│           React 18 + Vite + TailwindCSS Research Workspace UI          │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTP / REST & Dispatched Runs
┌────────────────────────────────────▼───────────────────────────────────┐
│                           API GATEWAY LAYER                            │
│                 FastAPI (CORS, Auth, Exception Handlers)               │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ Thread-Safe Dispatched Runs
┌────────────────────────────────────▼───────────────────────────────────┐
│                      LANGGRAPH ORCHESTRATION LAYER                     │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────────────────┐  │
│  │  Supervisor  ├────►│ Search Node  ├────►│  RAG Ingest & Retrieve │  │
│  └──────┬───────┘     └──────▲───────┘     └───────────┬────────────┘  │
│         │ (invalid)          │                         │               │
│         ▼                    │ (targeted query)        ▼               │
│        END     ┌─────────────┴┐     ┌──────────────┐   ┌────────────┐  │
│        ▲       │Targeted Query│     │ Sufficiency  │◄──┤  Summary   │  │
│        │       └──────────────┘     └──────┬───────┘   └─────┬──────┘  │
│        │                                   │                 │         │
│        │ (stop)     ┌──────────────┐       │ (continue)      │         │
│        └────────────┤ Final Report │◄──────┴─────────────────┘         │
│                     └──────────────┘                                   │
└──────────────────────┬───────────────────────────────┬─────────────────┘
                       │                               │
┌──────────────────────▼───────┐             ┌─────────▼─────────────────┐
│      PERSISTENCE LAYER       │             │   INTELLIGENCE SERVICES   │
│ - SQLite State Checkpointer  │             │ - Google GenAI SDK        │
│ - ChromaDB Persistent Client │             │ - Query Planner & Ranker  │
│ - In-Memory Session Storage  │             │ - Scholarly Providers     │
│                              │             │ - ResearchIntelligence    │
│                              │             │ - Stage 5 ResearchLoop    │
└──────────────────────────────┘             └───────────────────────────┘
```

---

## 2. Backend & Search Layer Architecture

- **`app/core/config.py`**: Centralized configuration management using Pydantic `BaseSettings`. Bounded search limits (`MAX_SEARCH_VARIANTS`, `MAX_RESULTS_PER_PROVIDER`, `MAX_TOTAL_CANDIDATES`, `MAX_FINAL_RETRIEVAL_PAPERS`, `SEARCH_TIMEOUT_SECONDS`, `RETRIEVAL_TOP_K`, `CHUNK_SIZE`, `CHUNK_OVERLAP`).
- **`app/core/logging.py`**: Structured logging facility equipped with `SecretSanitizingFormatter`.
- **`app/core/exceptions.py`**: Typed domain exception hierarchy (`ResearchAssistantError`, `LLMValidationError`, `SearchRetrievalError`, etc.).
- **`app/services/llm_service.py`**: Modern `google-genai` structured output service with Pydantic response schemas.
- **`app/search/`**:
  - `query_planner.py`: Authoritative query planning producing `SearchPlan`.
  - `base.py`: Abstract `SearchProvider` contract.
  - `arxiv_provider.py`: Scholarly arXiv Atom XML retrieval client.
  - `local_provider.py`: Local ChromaDB indexed corpus provider.
  - `deduplication.py`: Deterministic identity hierarchy (DOI -> Provider ID -> URL -> Title/Author).
  - `ranker.py`: Query-dependent relevance ranker (no hardcoded topic keywords).
  - `engine.py`: `ResearchSearchEngine` orchestrator with limit enforcement and telemetry.
- **`app/rag/`**:
  - `chunker.py`: Sentence-aware overlapping chunker with provenance.
  - `vector_store.py`: Deterministic chunk IDs `paper:{id}:chunk:{idx}_{hash}` and upsert.
  - `retriever.py`: Genuine vector store query returning `RetrievedDocument` objects.
  - `evidence.py`: Strongly-typed `EvidenceChunk` and session-scoped `EvidenceRegistry` with deterministic `E001` IDs.
  - `evidence_retriever.py`: `EvidenceRetriever` with candidate scope filtering, text deduplication, and score thresholding.
  - `context_builder.py`: `EvidenceContextBuilder` formatting demarcated evidence blocks and anti-hallucination prompts.
  - `claim_validator.py`: `ClaimEvidenceValidator` and `CitationVerifier` with verbatim quote integrity checking.
- **`app/intelligence/` (Stage 4 Research Intelligence)**:
  - `methodology_comparator.py`: `MethodologyComparator` extracting observed dimensions with null preservation.
  - `contradiction_detector.py`: `ContradictionDetector` distinguishing genuine result contradictions from dataset/methodology differences.
  - `cross_paper_analyzer.py`: `CrossPaperAnalyzer` synthesizing grounded agreements, disagreements, and qualified conclusions while eliminating ungrounded "all studies agree" assertions.
  - `evidence_strength_evaluator.py`: `EvidenceStrengthEvaluator` computing explainable ratings (STRONG, MODERATE, LIMITED, MIXED, INSUFFICIENT) with zero fake numerical percentages.
  - `research_gap_detector.py`: `ResearchGapDetector` deriving categorized gaps with mandatory "Within the retrieved literature..." prefix.
  - `consensus_synthesizer.py`: `ConsensusSynthesizer` generating multi-study narrative synthesis.
  - `provenance_guard.py`: `ProvenanceGuard` enforcing end-to-end evidence chain and purging hallucinated IDs.
  - `engine.py`: `ResearchIntelligenceEngine` orchestrating the complete analytical pipeline.
- **`app/loop/` (Stage 5 Agentic Research Loop)**:
  - `evaluator.py`: `EvidenceSufficiencyEvaluator` evaluating 5 qualitative sufficiency tiers and enforcing safety limits.
  - `gap_analyzer.py`: `ActionableGapAnalyzer` extracting grounded actionable gaps from contradictions, unsupported claims, and concentration.
  - `query_planner.py`: `TargetedQueryPlanner` formulating strategy-aligned follow-up queries with LLM and offline heuristic fallback.
  - `drift_guard.py`: `QueryDriftGuard` enforcing parent keyword retention and preventing topic drift.
  - `loop_controller.py`: `ResearchLoopController` managing multi-iteration state, paper deduplication, and structured telemetry.

---

## 3. LangGraph Execution Flow & State

### Authoritative State (`ResearchState`)
```python
class ResearchState(TypedDict):
    thread_id: str
    query: str
    retry_count: int
    execution_status: str

    supervisor: Optional[Dict[str, Any]]
    search_plan: Optional[Dict[str, Any]]
    papers: List[Dict[str, Any]]
    retrieved_documents: List[Dict[str, Any]]
    
    # Stage 3 Grounded Evidence State
    evidence_registry: Optional[Dict[str, Any]]
    claims: List[Dict[str, Any]]
    grounded_summary: Optional[Dict[str, Any]]
    citation_verification: Optional[Dict[str, Any]]
    grounding_status: str

    summaries: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    verification: Optional[Dict[str, Any]]
    gaps: Optional[Dict[str, Any]]
    intelligence: Optional[Dict[str, Any]]

    # Stage 4 Research Intelligence State
    cross_paper_findings: Optional[List[Dict[str, Any]]]
    study_comparisons: Optional[List[Dict[str, Any]]]
    contradiction_findings: Optional[List[Dict[str, Any]]]
    evidence_strength: Optional[Dict[str, Any]]
    research_gaps: Optional[List[Dict[str, Any]]]
    consensus_synthesis: Optional[Dict[str, Any]]

    # Stage 5 Agentic Research Loop State
    loop_state: Optional[Dict[str, Any]]
    current_iteration: int
    max_iterations: int
    sufficiency_evaluation: Optional[Dict[str, Any]]
    actionable_gaps: Optional[List[Dict[str, Any]]]
    research_decision: Optional[Dict[str, Any]]
    iterations_history: Optional[List[Dict[str, Any]]]

    report: str
    final_report: Optional[Dict[str, Any]]

    agent_logs: Annotated[List[Dict[str, Any]], operator.add]
    errors: Annotated[List[Dict[str, Any]], operator.add]
```

### Node Execution Responsibilities
1. **`supervisor` (`supervisor_node`)**: Evaluates academic validity; refines query if retryable.
2. **`supervisor_router`**: Routes to `END` if invalid; otherwise routes to `search`.
3. **`search` (`search_node`)**: Executes `ResearchSearchEngine.search()`. Generates `SearchPlan`, queries arXiv and local corpus, deduplicates against cumulative history, ranks against query, and populates `state["papers"]` and `state["search_plan"]`.
4. **`search_router`**: Routes to `END` if zero candidate papers found; otherwise routes to `rag`.
5. **`rag` (`rag_node`)**: Ingests candidate papers into ChromaDB; executes `EvidenceRetriever.retrieve_evidence()` with accretion support (`existing_registry`), builds/updates session-scoped `EvidenceRegistry`, and populates `state["retrieved_documents"]` and `state["evidence_registry"]`.
6. **`summary` (`summary_node`)**: Generates structured, evidence-grounded claims (`ResearchClaim`) and grounded summary via `synthesize_grounded_research()`, and runs `ClaimEvidenceValidator` and `CitationVerifier`. Populates `state["claims"]`, `state["grounded_summary"]`, `state["citation_verification"]`, and `state["grounding_status"]`.
7. **`summary_router`**: Routes to `END` if no summaries available; otherwise routes to `citation`.
8. **`citation` (`citation_node`)**: Generates deterministic APA, IEEE, MLA, and BibTeX citations (`CitationItem`).
9. **`intelligence` (`intelligence_node`)**: Executes `ResearchIntelligenceEngine` performing cross-paper analysis, agreement/disagreement detection, contradiction analysis, methodology comparison, evidence strength evaluation, research gap detection, and consensus synthesis with full provenance checking.
10. **`sufficiency` (`sufficiency_node`)**: Evaluates evidence sufficiency (`EvidenceSufficiencyEvaluator`), extracts grounded actionable gaps (`ActionableGapAnalyzer`), evaluates safety stop conditions, updates iteration audit log, and populates `state["sufficiency_evaluation"]`, `state["actionable_gaps"]`, `state["research_decision"]`, and `state["loop_state"]`.
11. **`sufficiency_router`**: Routes to `targeted_query` if decision is `CONTINUE_RESEARCH`; routes to `report` if `STOP_RESEARCH`.
12. **`targeted_query` (`targeted_query_node`)**: Selects top prioritized gap, formulates targeted search query via `TargetedQueryPlanner`, validates against `QueryDriftGuard`, advances iteration counter, and routes back to `search`.
13. **`report` (`report_node`)**: Generates final academic brief with Agentic Research Loop Trace Table, Study Comparison Matrix, Contradiction Analysis, Evidence Strength Assessment, Research Gaps, Verified Claims (`[E001]`), and Citation Audit.

---

## 4. Stage Boundaries & Future Evolution

| Architecture Domain | Stage 1 (Foundation) | Stage 2 (Search & Retrieval Engine) | Stage 3 (Real RAG & Grounding) | Stage 4 (Research Intelligence) | Stage 5 (Agentic Research Loop) | Stage 6 (Research Workspace UI) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Query Planning** | Heuristic query rewriter | Canonical `SearchPlan` (variants, concepts, intent) | Consumed | Analytical query expansion | Strategy-aligned targeted queries with anti-drift protection | User query input (2-1000 chars) & session isolation |
| **Search Providers** | Direct unvalidated arXiv calls | `SearchProvider` abstraction (arXiv + Local Corpus) | Consumed | Additional scholarly providers | Cumulative multi-pass retrieval with paper deduplication | Provider attribution and direct canonical DOI / URL navigation |
| **Deduplication** | None | Deterministic hierarchy (DOI, Provider ID, URL, Title/Author) | Consumed | Cross-edition deduplication | Cumulative history deduplication preventing false progress | Paper deduplication preserved in Source Explorer cards |
| **Vector Store** | Ingestion without retrieval | Deterministic IDs, sentence chunking, active query retrieval | Candidate-scoped vector retrieval | Full-text PDF chunking | Incremental evidence chunk accretion (`E001` -> `E005`...) | Chunk viewer with section, page, and retrieval scores |
| **Evidence Grounding**| Out of scope | Interface prepared | Deterministic registry, claim mapping, quote integrity | Cross-paper consensus & contradictions | Mandatory per-iteration grounding gate (no unverified claims) | Bidirectional Provenance Drawer: Finding -> Claim -> Evidence -> Paper -> Source |
| **Synthesis** | Unstructured summary | Basic summary schema | Schema-constrained grounded synthesis (`ResearchClaim`) | Deep analytical intelligence & matrix | Iterative multi-pass synthesis with full provenance audit trail | Multi-panel Research Workspace with qualitative metrics and zero fake data |

---

## 5. Persistence Architecture

1. **LangGraph Checkpoint Storage**:
   - Managed via `SqliteSaver` in `app/db/checkpoint.py`.
   - File path resolved absolutely (`settings.SQLITE_DB_PATH`).
   - Run thread IDs generated with unique session hashes and timestamps (`thread_{hash}_{timestamp}`) to avoid race conditions and state collisions.
2. **Vector Database**:
   - Managed via `chromadb.PersistentClient` in `app/rag/vector_store.py`.
   - Deterministic chunk hashing: `paper:{clean_paper_id}:chunk:{idx}_{hash}`.
   - Full metadata indexing (authors, URL, published date, chunk index, year, doi, journal_ref).
3. **Session State**:
   - Managed via `app/memory/memory_manager.py`.

---

## 6. Stage 6 Presentation Layer Architecture (Research Workspace)

The Stage 6 Presentation Layer replaces the single-page prototype with a modular, scholarly research workspace:

### Component Hierarchy (`frontend/src/components/workspace/`)
```
App.jsx (Root state & session orchestration)
├── WorkspaceHeader (Query validation, status badge, session ID input)
├── WorkspaceNav (9-view accessible tab bar with live entity counts)
├── Viewport Router:
│   ├── OverviewPanel (Executive synthesis, qualitative evidence strength, metrics, top findings)
│   ├── FinalReportPanel (Sanitized research brief reader, multi-format citation export)
│   ├── FindingsClaimsPanel (Stage 4 findings, Stage 3 claims with SUPPORTED / UNSUPPORTED badges)
│   ├── EvidenceExplorer (Verbatim excerpts, chunk IDs [E001], retrieval scores, source provenance)
│   ├── SourceExplorer (Normalized paper cards, DOIs, collapsible abstracts, linked evidence badges)
│   ├── ContradictionPanel (Contradiction cards vs methodology/population differences)
│   ├── MethodologyMatrix (Cross-paper comparative parameter matrix preserving nulls as '—')
│   ├── ResearchGapPanel (Empirical gap findings with 'Within the retrieved literature...' scope)
│   └── ResearchTracePanel (Stage 5 multi-turn iteration history & real agent execution logs)
├── ProvenanceDrawer (Slide-over bidirectional entity inspection dialog)
├── EmptyState (Honest, context-specific empty states)
└── ErrorState (Non-leaking error banner with retry capability)
```

### Key Architectural Tenets
1. **Authoritative Backend Contract**: Consumes the full `ResearchState` dictionary without frontend recalculation of claims, contradictions, or gaps.
2. **End-to-End Provenance Navigation**: Deep clickable linking from Finding $\rightarrow$ Claim $\rightarrow$ Evidence $\rightarrow$ Paper $\rightarrow$ External Source.
3. **Zero Fake Metrics & Activity**: Strictly qualitative evidence strength (`STRONG`, `MODERATE`, `LIMITED`, `MIXED`, `INSUFFICIENT`). No simulated progress timers or fabricated confidence percentages.
4. **XSS & Link Security**: Dedicated AST tokenizing `SafeMarkdown` component avoiding `dangerouslySetInnerHTML`. Protocol-safe external URL validation (`http/https` only with `rel="noopener noreferrer"`).
5. **Accessibility Baseline**: Semantic HTML5 landmark tags, full keyboard tab navigation, visible high-contrast focus rings, and WCAG AA contrast compliance.

---

## 7. Stage 7 Production Engineering Architecture

Stage 7 hardens the Research Intelligence Assistant for multi-tenant, high-concurrency, asynchronous production usage:

### 1. Authentication & Multi-Tenant Authorization
- **Identity Provider**: Built-in credential identity using `passlib` with modern PBKDF2-SHA256 and BCrypt password hashing.
- **JWT Authorization**: Cryptographically signed access tokens (HMAC-SHA256) enforcing standard expiration and claims validation.
- **Tenant Isolation**: Mandatory `user_id` ownership relations across `ResearchSession`, `ResearchRun`, `ResearchJob`, and `ReportModel`. Server-side dependencies enforce that User A cannot read, mutate, or stream User B's resources.

### 2. Durable Persistence (PostgreSQL with SQLite Fallback)
- **Engine**: Connection-pooled SQLAlchemy engine (`QueuePool` for PostgreSQL, `StaticPool` for local SQLite development fallback).
- **Alembic Migrations**: Version-controlled migrations tracking relational schema evolution with explicit foreign key constraints and query indexes (`user_id`, `session_id`, `status`, `created_at`).

### 3. Asynchronous Job & Worker Lifecycle
- **Job Orchestration**: Non-blocking `JobManager` wrapping `ThreadPoolExecutor` workers.
- **Explicit Lifecycle**: States transition strictly through `QUEUED` $\rightarrow$ `RUNNING` $\rightarrow$ `COMPLETED` / `FAILED` / `CANCELLED`.
- **Resource Constraints**: Server-side concurrency caps (max 2 concurrent jobs per user, max 10 concurrent jobs globally).
- **Idempotency Protection**: Active jobs reject duplicate simultaneous execution requests via client-provided `idempotency_key`.
- **Cooperative Cancellation**: Active jobs can be cancelled safely by their owner without durable state corruption.

### 4. Real-Time Server-Sent Events (SSE)
- **Event Bus**: In-memory pub-sub `JobEventBus` streaming authentic execution state (`research_started`, `agent_log`, `research_completed`, `research_failed`, `research_cancelled`).
- **Resilience**: 15-second heartbeat pings and circular event buffer replaying recent history upon reconnection.
- **Tenant Security**: Subscriptions require valid JWT auth tokens and ownership verification.

### 5. API Hardening & Observability
- **Rate Limiting**: `slowapi` rate limiting with IP and authenticated user awareness.
- **Security Headers**: Enforced via `SecurityHeadersMiddleware` (`nosniff`, `DENY` frames, strict referrer, zero cache on sensitive APIs).
- **Request Body Limits**: 1MB payload ceiling rejecting oversized POST submissions with HTTP 413.
- **Secret Scrubbing**: Regex filters automatically scrub API keys (`AIzaSy...`), JWTs, and passwords from log records.
- **Metrics**: `ObservabilityRegistry` tracking request rates, latencies, job status counts, and exporting standard Prometheus and JSON telemetry.
- **Correlation IDs**: ContextVar-based tracking injecting `X-Request-ID`, `user_id`, and `job_id` across HTTP requests, background workers, and logs.

---

## 8. Stage 8 Testing & Evaluation Architecture

Stage 8 incorporates a dedicated, decoupled evaluation package (`evaluation/`) designed to evaluate whether the multi-stage research assistant genuinely produces grounded, reproducible, and verifiable research intelligence:

### 1. Architectural Structure
```
evaluation/
├── datasets/           # Versioned golden datasets (v1.0.0, Cases A through N)
├── judges/             # Constrained rubric-based LLM-as-judge interface
├── metrics/            # Pure mathematical functions (Precision@K, Hit@K, MRR, Provenance, Drift)
├── runners/            # Specialized dimensional runners (Retrieval, RAG, Claims, Intelligence, Loop, Adversarial, Security)
├── reporters/          # Machine-readable JSON and human-readable Markdown report generators
├── quality_gates.py    # Explicit Hard and Informational quality gates
├── taxonomy.py         # Formal 22-category Failure Taxonomy and typed Enums
└── run_evaluation.py   # CLI entrypoint and evaluation orchestrator
```

### 2. Core Architectural Guarantees
- **Golden Dataset v1.0.0**: 14 representative scientific research cases evaluating straightforward biomedical efficacy, multi-technology comparisons, epidemiological contradictions, unaddressed gaps, and honest insufficient evidence reporting.
- **20 Deterministic Adversarial Red-Team Checks**: Testing fabricated citation identifiers, quote modifications, causal inference overreach from correlation, population/outcome substitutions, query drift, and schema failure degradation.
- **5 Hard Quality Gates**: Enforcing 100% citation validity, academic provenance completeness, adversarial defense, zero security regression, and honest reporting of insufficient evidence without manufactured consensus.
- **Regression Invariance**: Preserves existing Stage 1–7 test suites (117 backend pytest tests, 19 frontend Vitest tests, ESLint, and production Vite bundle).
- **Strict Stage 9 Boundary**: Formal evaluation and testing completed in Stage 8 before passing to Stage 9 production release.

---

## 9. Stage 9 Deployment & Production Release Architecture

Stage 9 hardens the Research Intelligence Assistant for multi-instance, production-grade cloud deployment, durable security, high-reliability execution, automated disaster recovery, and public-release compliance:

### 1. Multi-Stage Containerization & Orchestration
- **Backend Container (`Dockerfile`)**: Built on `python:3.13-slim` using multi-stage compilation. Operates under unprivileged `appuser` (UID 10001). Pre-configured with container healthchecks probing `/health/liveness` via curl.
- **Frontend Container (`frontend/Dockerfile`)**: Multi-stage build leveraging `node:22-alpine` for production asset compilation (`npm run build`) and unprivileged `nginx:1.27-alpine` for static serving.
- **Nginx Reverse Proxy (`frontend/nginx.conf`)**:
  - Injects mandatory security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, Strict CSP).
  - Handles SPA client-side routing fallback (`try_files $uri $uri/ /index.html`).
  - Proxies authenticated API paths (`/auth`, `/sessions`, `/research`, `/jobs`, `/health`) to backend service.
  - Configures SSE streaming proxy (`/stream`) with `proxy_buffering off`, `proxy_cache off`, and persistent connection headers.
- **Docker Compose Orchestration (`docker-compose.yml`)**: Coordinates PostgreSQL 16 database, backend API service, and frontend web server with healthcheck dependencies and isolated bridge network.

### 2. Multi-Instance Durable Token Revocation
- **Relational Revocation Store (`RevokedToken`)**: Persistent database model tracking revoked JWT access tokens via SHA-256 token hashing (`token_hash`), expiration timestamps (`expires_at`), and user association (`user_id`).
- **Dual-Tier Cache Strategy**:
  - L1 Fast Cache: Thread-safe in-memory cache for ultra-fast validation of recently revoked tokens.
  - L2 Persistent Store: PostgreSQL relational lookup ensuring token revocations survive container restarts and propagate seamlessly across horizontally scaled backend worker nodes.
- **Scheduled Expiration**: Revocations are bound to JWT expiration lifetimes, preventing unbounded database growth.

### 3. Worker Reliability & Crash Recovery
- **Orphan Job Detection (`recover_stale_jobs`)**: Automatically invoked during FastAPI application startup lifespan.
- **Crash Recovery**: Queries all jobs remaining in `QUEUED` or `RUNNING` status from prior process lifetimes and transitions them to `FAILED` with explicit `error_code="PROCESS_INTERRUPTED"`.
- **Honest Telemetry**: Ensures users are never confronted with eternal spinning loading states or zombie jobs following node restarts or server crashes.

### 4. Production Health & Readiness Probes
- **Liveness Probe (`/health/liveness`)**: Evaluates basic process responsiveness, returning `200 OK` with `{"status": "alive"}`.
- **Readiness Probe (`/health/readiness`)**: Actively validates external database connectivity via `SELECT 1` execution against the PostgreSQL engine pool, returning `200 OK` with `{"status": "ready", "database": "connected"}` or `503 Service Unavailable` if the database is unreachable.

### 5. Automated Disaster Recovery & Backups
- **Backup Engine (`scripts/backup_db.py`)**: Transactionally extracts all core relational models (`users`, `revoked_tokens`, `research_sessions`, `research_runs`, `research_iterations`, `research_jobs`, `research_reports`) into canonical JSON snapshots accompanied by cryptographic SHA-256 integrity checksums and migration metadata.
- **Restore Engine (`scripts/restore_db.py`)**: Re-computes and verifies SHA-256 backup checksums prior to execution, cleans target tables in strict foreign-key dependency order, and repopulates all tables with primary-key preservation.

### 6. Public Release Compliance & Legal Foundations
- **Legal Modals (`LegalModal.jsx`)**: WCAG AA accessible modal dialogs presenting genuine, comprehensive Privacy Policy and Terms of Service agreements.
- **Scholarly Aesthetic Compliance**: Completely free of purple gradients, pill-shaped buttons, fake progress, fake metrics, fake testimonials, AI-slop copy, or "Made with AI" badges.
- **Safe Environment Templates**: Fully documented `.env.example` defining all production parameters without real secrets or demo credentials.


