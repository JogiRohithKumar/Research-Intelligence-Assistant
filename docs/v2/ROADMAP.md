# RESEARCH-INTELLIGENCE-ASSISTANT V2 ROADMAP
**Status:** COMPLETE & VERIFIED  
**Current Stage:** Stage 9 — Deployment & Production Release (COMPLETE & VERIFIED)  
**Roadmap Status:** 9 OF 9 STAGES COMPLETE & LOCKED — NO STAGE 10 EXISTS  

This is the STRICT 9-STAGE implementation roadmap for the V2 rebuild of **Research-Intelligence-Assistant**. Stages cannot be skipped, combined, or prematurely implemented. There is no Stage 10.

---

## 1. Stage 1 — Foundation & Architecture (COMPLETE & APPROVED)
- **Objective:** Establish a clean, reliable, and strictly typed architectural foundation.
- **Key Deliverables:**
  - Full codebase inspection and baseline audit documentation.
  - V2 Core State architecture using Pydantic models for domain entities.
  - Structured LLM output engine replacing regex/JSON extraction.
  - Clean LangGraph state graph foundation with explicit routing and error representation.
  - Centralized application configuration layer with typed environment settings.
  - Elimination of hardcoded secrets and dangerous default credentials.
  - Structured application logging and predictable error handling foundation.
  - Audit of dead and duplicate code without destructive deletions.
  - Baseline smoke tests validating backend startup, graph compilation, schema validation, and frontend compilation.
  - Architecture and roadmap documentation.

---

## 2. Stage 2 — Research Search & Retrieval Engine (COMPLETE & VERIFIED)
- **Objective:** Build a robust, query-driven scholarly research retrieval engine.
- **Key Deliverables:**
  - Canonical single-source-of-truth Query Planner (`SearchPlan`).
  - Search Provider abstraction (`SearchProvider`) with ArXiv and Local Corpus providers.
  - Robust paper deduplication engine (DOI, Provider ID, URL, Title/Author).
  - Explainable query-dependent relevance ranker without topic bias.
  - Bounded candidate, provider, and variant limits.
  - Canonical normalized paper model (`NormalizedPaper`) preserving provenance.
  - Sentence-aware overlapping chunker (`chunk_document`).
  - Deterministic vector store upsert and actual vector query retrieval in graph execution.
  - Graceful failure handling and non-sensitive structured telemetry.
  - Comprehensive automated test suite (32 unit tests passing).

---

## 3. Stage 3 — Real RAG & Evidence Grounding (COMPLETE & VERIFIED)
- **Objective:** Build genuine end-to-end RAG with evidence extraction and citation grounding.
- **Key Deliverables:**
  - Canonical strongly-typed `EvidenceChunk` and session-scoped `EvidenceRegistry`.
  - Deterministic evidence identifiers (`E001`, `E002`, ...).
  - Dedicated `EvidenceRetriever` with candidate scope filtering, text deduplication, and score thresholds.
  - Dedicated `EvidenceContextBuilder` formatting demarcated blocks with strict anti-hallucination instructions.
  - Structured research claims (`ResearchClaim`, `ClaimSupportStatus`, `ClaimType`).
  - Machine-readable Claim -> Evidence mapping (`evidence_ids`).
  - Strict `ClaimEvidenceValidator` rejecting phantom evidence IDs and flagging unsupported claims.
  - Dedicated `CitationVerifier` with source resolution and verbatim quote integrity validation.
  - Elimination of fake confidence scores and metrics in final report output.
  - Comprehensive automated test suite (58 total tests passing, 26 Stage 3 unit & adversarial tests).

---

## 4. Stage 4 — Research Intelligence (COMPLETE & VERIFIED)
- **Objective:** Separate deep analytical intelligence into dedicated, rigorous specialist agents and engine.
- **Key Deliverables:**
  - Canonical Stage 4 domain models (`ResearchFinding`, `PaperComparison`, `ContradictionFinding`, `EvidenceStrength`, `ResearchGapFinding`, `ConsensusSynthesis`, `ResearchIntelligenceReport`).
  - Grounded `MethodologyComparator` extracting observed dimensions with null preservation.
  - Nuanced `ContradictionDetector` distinguishing genuine result contradictions from dataset/methodology differences.
  - Evidence-grounded `CrossPaperAnalyzer` detecting agreement, disagreement, and qualified conclusions while eliminating ungrounded "All studies agree" claims.
  - Interpretable `EvidenceStrengthEvaluator` classifying evidence strength (STRONG, MODERATE, LIMITED, MIXED, INSUFFICIENT) with zero fake numerical percentages.
  - Structured `ResearchGapDetector` deriving empirical gaps with mandatory "Within the retrieved literature..." scope.
  - Grounded `ConsensusSynthesizer` generating multi-study narrative synthesis and honestly handling insufficient or mixed evidence.
  - Strict `ProvenanceGuard` enforcing end-to-end chain from findings to Stage 3 claims and evidence chunks.
  - Coherent LangGraph state integration and rich academic brief generation in `report_node`.
  - Comprehensive automated test suite (16 Stage 4 tests, 74 total suite tests passing).

---

## 5. Stage 5 — Agentic Research Loop (COMPLETE & VERIFIED)
- **Objective:** Implement an evidence-driven, bounded multi-turn agentic research cycle.
- **Key Deliverables:**
  - Typed Stage 5 domain models (`SufficiencyStatus`, `EvidenceSufficiency`, `ResearchStopReason`, `ActionableResearchGap`, `TargetedResearchQuery`, `ResearchDecision`, `ResearchIteration`, `ResearchLoopState`).
  - Deterministic `EvidenceSufficiencyEvaluator` with 5 qualitative tiers (zero fake percentages).
  - Grounded `ActionableGapAnalyzer` extracting gaps from contradictions, unsupported claims, and concentration.
  - Strategy-aligned `TargetedQueryPlanner` with structured LLM reasoning and offline deterministic fallback.
  - `QueryDriftGuard` enforcing parent keyword retention and preventing topic drift.
  - `ResearchLoopController` managing multi-iteration state, deduplication against cumulative history, and no-progress termination.
  - Seamless evidence accretion in `EvidenceRetriever` preserving sequential chunk IDs (`E001` -> `E005`...).
  - Full LangGraph pipeline integration (`sufficiency_node` -> `sufficiency_router` -> `targeted_query_node` -> `search_node`).
  - Hard server-side safety limits (max iterations, max search calls, duplicate query/paper prevention).
  - Structured loop telemetry and observability without credential logging.
  - Comprehensive automated test suite (16 Stage 5 tests, 90 total suite tests passing).

---

## 6. Research Workspace UI (COMPLETE & VERIFIED)
- **Objective:** Transform the user interface into a high-performance research workspace.
- **Key Deliverables:**
  - Modern Consensus / Elicit inspired scholarly research intelligence workspace.
  - Accessible multi-panel tab navigation across 9 specialized research inspection views.
  - Real Stage 5 Agentic Research Loop Trace visualizer rendering actual multi-turn iterations.
  - Dual-column Findings & Claims Inspector displaying explicit SUPPORTED and UNSUPPORTED states.
  - Verbatim Evidence Explorer with chunk IDs (`[E001]`), retrieval scores, section, and page provenance.
  - Normalized Source / Paper Explorer with external DOI links, expandable abstracts, and evidence tags.
  - Nuanced Contradiction Panel distinguishing genuine scientific contradictions from methodology/population differences.
  - Structured Methodology Matrix preserving unobserved parameters as null values (`—`).
  - Empirical Research Gap Panel with severity rating and mandatory "Within the retrieved literature..." qualification.
  - Purely qualitative Evidence Strength display (STRONG, MODERATE, LIMITED, MIXED, INSUFFICIENT) with zero fake percentages.
  - Bidirectional Provenance Drawer navigating Finding -> Claim -> Evidence -> Paper -> Source.
  - Non-leaking error handling, honest empty states, and WCAG AA accessibility baseline.
  - Comprehensive automated frontend test suite (19/19 Vitest tests passing) and zero build errors.

---

## 7. Stage 7 — Production Engineering (COMPLETE & VERIFIED)
- **Objective:** Harden backend and frontend infrastructure for high concurrency, multi-tenancy, and security.
- **Key Deliverables:**
  - True Server-Sent Events (SSE) streaming per-session and per-job with `JobEventBus`.
  - Durable PostgreSQL schema + versioned Alembic migrations (with SQLite development fallback).
  - Server-side multi-tenant isolation, user authentication (PBKDF2/BCrypt, JWT), and authorization dependencies.
  - Asynchronous background execution with `JobManager`, ThreadPool concurrency limits, and cooperative cancellation.
  - Idempotency deduplication mechanism protecting expensive research executions.
  - Server-side rate limiting with `slowapi` on auth, job submission, and streaming endpoints.
  - Production observability registry exporting Prometheus and JSON metrics with ContextVar correlation IDs.
  - Request body size limits (1MB), security headers middleware, and secret scrubbing in logs.
  - Frontend production integration with real async status badges, cancel support, and EventSource subscription.
  - Full automated verification (110 backend tests passing, 19 frontend tests passing, 0 lint errors, 0 build errors).

---

## 8. Stage 8 — Testing & Evaluation (COMPLETE & VERIFIED)
- **Objective:** Comprehensive automated testing, empirical research quality evaluation, and adversarial red-teaming.
- **Key Deliverables:**
  - Dedicated decoupled evaluation package (`evaluation/`) with typed Pydantic models.
  - Versioned Golden Dataset (`v1.0.0`) containing 14 representative academic research cases (A through N).
  - 20 Deterministic Adversarial Red-Team benchmarks (fabricated citations, quote alterations, causal overreach, query drift, schema fallbacks).
  - Strict Quality Gates architecture enforcing 5 Hard Quality Gates (100% citation validity, provenance completeness, adversarial defense, zero security regression, honest insufficient evidence stance).
  - Multi-dimensional evaluation runners (`RetrievalRunner`, `RagRunner`, `ClaimsRunner`, `IntelligenceRunner`, `LoopRunner`, `AdversarialRunner`, `SecurityRunner`).
  - Standardized 22-category Failure Taxonomy tracking granular defect modes.
  - Machine-readable JSON and human-readable Markdown evaluation report generators.
  - Full automated regression test suites passing cleanly (117 backend pytest tests, 9 evaluation pytest tests, 19 frontend Vitest tests, 0 lint errors, 0 build errors).

---

## 9. Stage 9 — Deployment & Production Release (COMPLETE & VERIFIED)
- **Objective:** Production containerization, multi-instance persistence, security hardening, automated disaster recovery, and public release readiness.
- **Key Deliverables:**
  - Production multi-stage Dockerfiles for backend (Python 3.13 unprivileged) and frontend (Node 22 + Nginx 1.27 unprivileged).
  - Docker Compose orchestration with isolated bridge network and integrated healthchecks.
  - Multi-instance durable JWT token revocation using PostgreSQL (`revoked_tokens`) with dual L1/L2 cache and SHA-256 token hashing.
  - Automatic process crash and worker restart recovery (`recover_stale_jobs`) marking orphan in-flight tasks as `FAILED`.
  - Production health probes (`/health/liveness` and `/health/readiness` with live DB connectivity check).
  - Transactional database backup and restore scripts with SHA-256 cryptographic checksum verification (`scripts/backup_db.py`, `scripts/restore_db.py`).
  - Production-ready environment configuration (`.env.example`) with zero real secrets or demo credentials.
  - Public release legal foundations (accessible Privacy Policy and Terms of Service modals in `LegalModal.jsx`).
  - Comprehensive dependency audit, vulnerability remediation, and runtime dependency upgrades (`pydantic-settings`, `urllib3`, npm security upgrades).
  - End-to-end production smoke test and regression verification across all test suites.
  - **FINAL ROADMAP NOTE:** The 9-stage roadmap is officially COMPLETE and CONCLUDED. Stage 10 does not exist.

