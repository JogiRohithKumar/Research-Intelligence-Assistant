# STAGE 1 DEAD & DUPLICATED CODE AUDIT
**Project:** Research-Intelligence-Assistant (V2 Development Rebuild)  
**Date:** 2026-10-05  
**Stage:** Stage 1 — Foundation & Architecture  

---

## 1. Overview

Per Stage 1 guidelines, code is **not blindly deleted**. Each candidate has been classified with empirical evidence and a concrete recommendation (retain, refactor, or safely prune).

---

## 2. Backend Code Audit

| Item | Type | Evidence & Observation | Recommended Action | Stage Owner |
| :--- | :--- | :--- | :--- | :--- |
| `app/agents/verification_agent.py` | Orphaned Agent | Contains `verify_findings(summaries)` with Gemini prompting and regex JSON parsing. **Never imported or called in `research_graph.py` or any route.** | **RETAIN & REFACTOR**: Do not delete. Upgrade to structured Pydantic output and integrate into modular V2 graph foundation. | Stage 1 / Stage 4 |
| `app/agents/gap_agent.py` | Orphaned Agent | Contains `analyze_gaps(summaries)` with Gemini prompting and regex JSON parsing. **Never imported or called in `research_graph.py` or any route.** | **RETAIN & REFACTOR**: Do not delete. Upgrade to structured Pydantic output and integrate into modular V2 graph foundation. | Stage 1 / Stage 4 |
| `app/agents/human_review_agent.py` | Broken Module | Calls `choice = input("\nApprove summaries? (y/n): ")`. Blocks Python standard input; completely freezes asynchronous ASGI server processes. | **MARK OBSOLETE**: Replace terminal input with LangGraph interrupt/checkpoint or API-driven approval. Do not call in active graph. | Stage 5 |
| `app/api/search.py` | Unmounted Route | Defines `router = APIRouter()` with `GET /search`. `main.py` only mounts `app.api.routes` and `app.api.stream`. Never exposed to clients. | **SAFE PRUNE OR RETAIN AS UTILITY**: Can be mounted if direct search endpoint is desired, or removed. | Stage 2 |
| `app/workflows/research_workflow.py` | Empty File | File size is exactly 0 bytes. | **SAFE PRUNE**: Contains no logic. | Stage 1 |
| `backend/` (directory) | Empty Directory | Directory exists at repository root with 0 files. Actual backend logic is located entirely in `app/`. | **SAFE PRUNE**: Delete empty folder to eliminate directory ambiguity. | Stage 1 |
| `app/database/` (directory) | Empty Directory | Directory contains 0 files. Actual database files and SQLite connection are in `app/db/`. | **SAFE PRUNE**: Delete empty folder to eliminate directory ambiguity. | Stage 1 |
| `app/services/` (directory) | Empty Directory | Directory contains 0 files. | **SAFE PRUNE / RETAIN FOR V2**: Can hold V2 LLM and retrieval services. | Stage 1 |
| `app/utils/json_parser.py` vs inline `extract_json` | Duplicated Code | `extract_json` is implemented in `app/utils/json_parser.py`, but also copy-pasted into `supervisor_agent.py`, `summary_agent.py`, `research_intelligence_agent.py`, `verification_agent.py`, and `gap_agent.py`. | **REFACTOR**: Replace all regex JSON extractors with centralized Pydantic structured output. | Stage 1 |
| `app/memory/session_memory.py` vs `app/memory/memory_manager.py` | Duplicated State | Both files operate on the identical in-memory dictionary `research_sessions = {}`. `memory_manager.py` re-implements `save_session` and `load_session`. | **CONSOLIDATE**: Unify session management and mark in-memory storage for database persistence. | Stage 1 / Stage 7 |

---

## 3. Frontend Code Audit

| Item | Type | Evidence & Observation | Recommended Action | Stage Owner |
| :--- | :--- | :--- | :--- | :--- |
| `frontend/src/components/ChatMessage.jsx` | Unused Component | Defines a chat bubble component. Grep across `frontend/src` reveals zero import statements or references. | **RETAIN OR SAFE PRUNE**: Not referenced in `App.jsx`. Keep as UI asset or prune. | Stage 6 |
| `frontend/src/components/AgentProgress.jsx` | Unused Component | Defines an event checklist. Grep reveals zero import statements. `App.jsx` uses `AgentPanel.jsx` instead. | **SAFE PRUNE**: Superseded by `AgentPanel.jsx`. | Stage 1 / Stage 6 |
| `frontend/src/services/api.js` | Disconnected Service | Defines Axios functions `runResearch` and `getStream`. `App.jsx` bypasses this file with inline `fetch()` and hardcoded headers. | **REFACTOR**: Update `api.js` to include auth headers and dynamic URL, then wire into UI. | Stage 1 / Stage 6 |
| `frontend/src/pages/Dashboard.jsx` | 0-byte Stub | File size is 0 bytes. | **RETAIN AS PLACEHOLDER**: For Stage 6 multi-page workspace. | Stage 6 |
| `frontend/src/pages/Reports.jsx` | 0-byte Stub | File size is 0 bytes. | **RETAIN AS PLACEHOLDER**: For Stage 6 multi-page workspace. | Stage 6 |
| `frontend/src/pages/Results.jsx` | 0-byte Stub | File size is 0 bytes. | **RETAIN AS PLACEHOLDER**: For Stage 6 multi-page workspace. | Stage 6 |
| `frontend/src/services/stream.js` | 0-byte Stub | File size is 0 bytes. | **RETAIN AS PLACEHOLDER**: For Stage 7 SSE client. | Stage 7 |
| `frontend/src/store/researchStore.js` | 0-byte Stub | File size is 0 bytes. | **RETAIN AS PLACEHOLDER**: For Stage 6 Zustand/Redux state store. | Stage 6 |
| `frontend/src/hooks/useStream.js` | 0-byte Stub | File size is 0 bytes. | **RETAIN AS PLACEHOLDER**: For Stage 7 SSE hook. | Stage 7 |

---

## 4. Preservation Strategy for Stage 1

1. **Preserve Working Logic**:
   - ArXiv API request and XML parsing in `search_agent.py` (removing only the hardcoded keyword filter).
   - Citation generation rules (APA, IEEE, MLA, BibTeX) in `citation_agent.py`.
   - Report markdown compilation logic in `report_agent.py`.
   - Tailwind styling and layout in `frontend/src/App.jsx`.
2. **Safe Removal of True Dead Empty Directories**:
   - Prune empty `backend/` and `app/database/` directories which exist purely as abandoned folder artifacts.
