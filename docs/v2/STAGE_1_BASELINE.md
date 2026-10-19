# STAGE 1 BASELINE AUDIT REPORT
**Project:** Research-Intelligence-Assistant (V2 Development Rebuild)  
**Date:** 2026-10-05  
**Stage:** Stage 1 — Foundation & Architecture  
**Status:** Baseline Completed — Verified Against V2 Development Codebase  

---

## 1. Executive Summary

This document establishes the empirical baseline for the V2 rebuild of **Research-Intelligence-Assistant**. An exhaustive inspection was conducted across all backend services, LangGraph definitions, agent modules, RAG pipelines, API routers, frontend components, configuration files, and persistence mechanisms in the cloned development repository (`d:\volume c\REBUILD\multi-agent-research-assistant\multi-agent-research-assistant`).

All 20 previously suspected implementation deficiencies were empirically verified against the active source code.

---

## A. Current Architecture & Execution Flow

The current architecture is a monolithic FastAPI backend paired with a Vite + React + TailwindCSS frontend, orchestrating an ArXiv search pipeline through an early LangGraph StateGraph.

### Current Execution Flow:
1. **Frontend Request**: The React UI (`frontend/src/App.jsx`) initiates polling via `setInterval` every 1,000ms to `GET /stream`, then issues an HTTP POST request to `/research` containing `{ "query": "..." }` and an `x-api-key` header with a hardcoded demo token.
2. **FastAPI Ingestion**: `app/api/routes.py` receives the request, validates the header against a hardcoded list in `app/auth/api_keys.py`, and sets `thread_id = request.query`.
3. **Graph Execution (`app/graph/research_graph.py`)**:
   - `START` → `supervisor_node`: Invokes Gemini 2.5 Flash via legacy `google.generativeai` with a query validation prompt. Returns JSON parsed by regex.
   - `supervisor_router`: If `status == "invalid"`, routes to `END`. Otherwise unconditionally routes to `search_node` (even if `retry` was requested).
   - `search_node`: Rewrites the query using Gemini, issues an HTTP request to the ArXiv Atom API (`export.arxiv.org`), parses XML, and filters results against a static keyword whitelist (`llm`, `gpt`, `transformer`, `education`, etc.).
   - `search_node` → `rag_node`: Slices paper abstracts into 1,000-character chunks and inserts them into ChromaDB (`app/db/chroma`) with random UUIDs and minimal metadata (`{"title": ...}`). Does **not** query or retrieve from ChromaDB.
   - `rag_node` → `summary_node`: Iterates over the raw ArXiv paper abstracts in memory and prompts Gemini to produce per-paper summaries and key findings, parsed via regex into a list of dictionaries.
   - `summary_router`: If summaries are empty, routes to `END`; otherwise routes to `citation_node`.
   - `citation_node`: Programmatically generates deterministic APA, IEEE, MLA, and BibTeX citation strings from the paper metadata.
   - `citation_node` → `intelligence_node`: Prompts Gemini with all summaries to generate verification findings and research gaps inside a single prompt call.
   - `intelligence_node` → `report_node`: Compiles a Markdown document combining query, summaries, verification, gaps, and APA citations. Saves the entire run to an in-memory dictionary `research_sessions`.
   - `report_node` → `END`.
4. **Frontend Response Handling**: The frontend receives the full JSON response, **ignores** the backend-generated Markdown report, and instead synthesizes its own client-side report object in React state before saving to browser `sessionStorage`.

---

## B. Current LangGraph Architecture

The active graph is implemented in `app/graph/research_graph.py` using `langgraph.graph.StateGraph`.

### 1. State Definition
```python
class ResearchState(TypedDict):
    thread_id: str
    query: str
    supervisor: dict
    papers: list
    summaries: list
    citations: list
    intelligence: dict
    report: str
    agent_logs: Annotated[list, operator.add]
```
*Critique*: Untyped dictionaries (`dict`) and untyped lists (`list`). No Pydantic domain models. `agent_logs` is the only reducer-annotated field.

### 2. Nodes in Active Graph
| Node Name | Function | Responsibilities | Output State Keys |
| :--- | :--- | :--- | :--- |
| `supervisor` | `supervisor_node` | Evaluates research query validity using Gemini | `supervisor` |
| `search` | `search_node` | Rewrites query, fetches ArXiv papers, filters by hardcoded keywords | `papers`, `agent_logs` |
| `rag` | `rag_node` | Naively chunks abstracts and inserts into ChromaDB (no retrieval) | `{}` |
| `summary` | `summary_node` | Generates per-paper summaries and findings | `summaries`, `agent_logs` |
| `citation` | `citation_node` | Deterministic citation string generation (APA, IEEE, MLA, BibTeX) | `citations`, `agent_logs` |
| `intelligence`| `intelligence_node`| Generates verification and gap analysis in one LLM call | `intelligence`, `report`, `agent_logs` |
| `report` | `report_node` | Assembles Markdown report string and writes to in-memory session | `report` |

### 3. Edges & Routing
- `START -> supervisor`
- `supervisor -[conditional: supervisor_router]-> search | END`
- `search -> rag`
- `rag -> summary`
- `summary -[conditional: summary_router]-> citation | END`
- `citation -> intelligence`
- `intelligence -> report`
- `report -> END`

### 4. Checkpointing
- In `app/db/checkpoint.py`, `checkpointer = SqliteSaver(conn)` where `conn = sqlite3.connect("app/db/research.db", check_same_thread=False)`.
- Thread ID is set to `request.query`. Repeating the same query re-uses the identical thread ID, causing state overwrites and checkpoint collisions.

---

## C. Current Agents Classification

| Agent / Module | Path | Status | Evidence & Reason |
| :--- | :--- | :--- | :--- |
| `supervisor_agent` | `app/agents/supervisor_agent.py` | **Partially Active / Flawed** | Active in graph, but retry logic is a no-op; uses regex JSON extraction and hardcoded model name. |
| `query_rewriter` | `app/agents/query_rewriter.py` | **Partially Active / Flawed** | Called synchronously inside `search_agent.py`, but prompt contains accidental copy-pasted RAG grounding instructions (`"If paper is NOT in dataset..."`). |
| `search_agent` | `app/agents/search_agent.py` | **Active / Flawed** | Active in graph; executes ArXiv search, but filters candidates with a hardcoded keyword whitelist (`important = ["llm", "gpt", ...]`). |
| `summary_agent` | `app/agents/summary_agent.py` | **Active / Flawed** | Active in graph; summarizes papers, but uses fragile regex parsing that fails on top-level JSON arrays. |
| `citation_agent` | `app/agents/citation_agent.py` | **Active** | Active in graph; pure Python string formatting for citation standards. Deterministic and functional. |
| `research_intelligence_agent` | `app/agents/research_intelligence_agent.py` | **Active / Flawed** | Combines verification and gaps into one prompt; prompt contains raw Python syntax bug (`citations_text = ...`); bypasses dedicated verification and gap agents. |
| `verification_agent` | `app/agents/verification_agent.py` | **Unused / Orphaned** | Exists with full `verify_findings(summaries)` implementation, but is **never** imported or wired into `research_graph.py`. |
| `gap_agent` | `app/agents/gap_agent.py` | **Unused / Orphaned** | Exists with full `analyze_gaps(summaries)` implementation, but is **never** imported or wired into `research_graph.py`. |
| `human_review_agent`| `app/agents/human_review_agent.py`| **Broken / Unusable** | Contains `input("\nApprove summaries? (y/n): ")`. Blocks terminal standard input; completely crashes or freezes web server execution. |
| `report_agent` | `app/agents/report_agent.py` | **Partially Active** | Formats markdown report on backend, but output is ignored by frontend `App.jsx`. |

---

## D. Current API Layer

All routes are mounted via FastAPI in `main.py`.

| Route | Method | File | Purpose & Actual Behavior | Deficiencies |
| :--- | :--- | :--- | :--- | :--- |
| `/research` | `POST` | `app/api/routes.py` | Executes the LangGraph research graph for a user query. | Uses user query as `thread_id`; hardcoded API key check; blocking execution without true async stream. |
| `/stream` | `GET` | `app/api/stream.py` | Returns `{"events": [...]}` from in-memory global list. | Not SSE or WebSockets; polls global shared array; concurrent queries corrupt event history for all users. |
| `/search` | `GET` | `app/api/search.py` | Standalone endpoint calling `search_papers(query)`. | **Dead route**; not mounted in `main.py`; duplicates search execution outside the graph. |

---

## E. Current Frontend Architecture

The frontend is a single-page React 18 application built with Vite and TailwindCSS (`frontend/`).

### Major Components:
- `App.jsx`: Monolithic container holding search logic, stream polling via `setInterval`, state persistence to `sessionStorage`, and layout rendering.
- `Header.jsx`: Top navigation banner with title and static "BETA" badge.
- `QueryBox.jsx`: Form input handling query submission and loading state.
- `AgentPanel.jsx`: Timeline showing event log strings. Hardcodes `totalExpectedEvents = 5`.
- `ReportPanel.jsx`: Displays Executive Summary, Key Findings, Research Gaps, and Future Directions. Renders custom client-constructed object rather than backend report markdown.
- `PapersPanel.jsx`: Displays list of ArXiv papers with external links and authors.

### Dead / Unfinished Frontend Files:
- `frontend/src/components/ChatMessage.jsx`: Orphaned chat bubble component (never imported).
- `frontend/src/components/AgentProgress.jsx`: Orphaned progress component (never imported).
- `frontend/src/pages/Dashboard.jsx`: 0-byte placeholder.
- `frontend/src/pages/Reports.jsx`: 0-byte placeholder.
- `frontend/src/pages/Results.jsx`: 0-byte placeholder.
- `frontend/src/services/stream.js`: 0-byte placeholder.
- `frontend/src/store/researchStore.js`: 0-byte placeholder.
- `frontend/src/hooks/useStream.js`: 0-byte placeholder.
- `frontend/src/services/api.js`: Defines Axios wrappers, but is bypassed by `App.jsx` and lacks `x-api-key` headers.

---

## F. Current Data Flow

```
User Query (Frontend)
   │
   ▼ (POST /research with header 'x-api-key: research-assistant-demo-key')
FastAPI Route (`app/api/routes.py`)
   │ [Config: thread_id = request.query]
   ▼
LangGraph (`app/graph/research_graph.py`)
   │
   ├─► supervisor_node (Gemini 2.5 Flash -> Regex JSON parse)
   │      │
   │      ▼
   ├─► search_node (query_rewriter -> ArXiv XML fetch -> Static Whitelist Filter)
   │      │
   │      ▼
   ├─► rag_node (Naively chunk abstracts by 1,000 chars -> ChromaDB insert with UUIDs)
   │      │ [NOTE: Zero retrieval occurs. Stored embeddings are never queried!]
   │      ▼
   ├─► summary_node (Gemini 2.5 Flash -> Summarize in-memory abstracts -> Regex JSON)
   │      │
   │      ▼
   ├─► citation_node (Pure Python formatting -> APA, IEEE, MLA, BibTeX)
   │      │
   │      ▼
   ├─► intelligence_node (Gemini 2.5 Flash -> Verification + Gaps in 1 call)
   │      │
   │      ▼
   ├─► report_node (Python Markdown assembler -> In-memory dict save)
   │
   ▼ (Full JSON graph state returned to client)
Frontend (`frontend/src/App.jsx`)
   │ [Discards state.report; extracts summaries[0] + intelligence into custom object]
   ▼
Render UI (AgentPanel, ReportPanel, PapersPanel)
```

---

## G. Current Persistence Architecture

1. **SQLite Checkpointing (`app/db/research.db`)**:
   - Managed by `SqliteSaver` in `app/db/checkpoint.py`.
   - File is checked into git (`research.db`, `research.db-wal`, `research.db-shm`).
   - Uses relative path `"app/db/research.db"`.
   - State schema is tightly bound to `ResearchState`.
2. **ChromaDB (`app/db/chroma/`)**:
   - Managed by `chromadb.PersistentClient(path="app/db/chroma")`.
   - Collection name: `"research_papers"`.
   - Ingestion is write-only. Every chunk gets a new random UUID. No deduplication, upsert, or retrieval.
3. **In-Memory Session Memory (`app/memory/session_memory.py` & `memory_manager.py`)**:
   - Stored in a module-level global dictionary: `research_sessions = {}`.
   - Overwritten on process reload. Not thread-safe or multi-worker safe.
4. **Local Event Log File (`logs.jsonl`)**:
   - `app/monitor/logger.py` appends JSON lines to a hardcoded `logs.jsonl` in the current working directory.

---

## H. Current Security Audit

> [!WARNING]
> Security Audit Findings (Values Sanitized in Accordance with Rules)

1. **Hardcoded API Keys in Repository**:
   - `app/auth/api_keys.py`: `VALID_API_KEYS` contains a plaintext demo key hardcoded in version control.
   - `frontend/src/App.jsx`: `const API_KEY = '...'` contains the hardcoded demo key exposed in clientside bundle.
2. **Environment Variable Secret Handling**:
   - Secret key `GEMINI_API_KEY` was detected in local `.env`.
   - No `.env.example` file existed prior to this stage.
   - Configuration in `app/config.py` does not validate key presence or formatting.
3. **CORS Configuration**:
   - `main.py` explicitly allows `allow_origin_regex=r"https://multi-agent-research-assistant-.*\.vercel\.app"` and `http://localhost:5173`.
   - `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
4. **Session & State Concurrency**:
   - Global mutable `stream_events = []` in `app/utils/stream_logger.py` causes cross-tenant log pollution.
   - Using `request.query` as `thread_id` leads to state overwrites between separate users searching identical terms.

---

## I. Current Testing Baseline

- **Unit Tests**: Zero tests found (`tests/` directory does not exist).
- **Integration Tests**: Zero tests found.
- **Coverage**: 0%.
- **Validation**: Smoke verification during this audit confirmed:
  - Frontend builds cleanly via `npm run build` (Vite v8.0.16).
  - Python dependencies load in virtual environment `.venv-2`.

---

## J. Current Deployment Assumptions

1. **Frontend**: Vite configured for static export. Hardcoded references to Vercel domains (`multi-agent-research-assistant-rho.vercel.app`) in CORS.
2. **Backend**: Assumes single-process Uvicorn execution. SQLite and ChromaDB paths assume working directory is the repository root (`app/db/...`).
3. **Docker**: No `Dockerfile` or `docker-compose.yml` present in repository.
4. **PaaS Configuration**: No `render.yaml`, `vercel.json`, or Procfile found.

---

## Conclusion & Stage 1 Scope

The baseline confirms that the codebase contains foundational ideas and working prototypes (ArXiv parsing, citation generation, basic LangGraph structure), but suffers from architectural coupling, fragile output parsing, hardcoded assumptions, and missing RAG grounding.

Stage 1 will implement:
1. Pydantic V2 core state schemas.
2. Centralized typed configuration layer.
3. Structured LLM output with graceful validation.
4. Clean, modular LangGraph foundation.
5. Standardized structured logging and error handling.
6. Baseline smoke tests.
