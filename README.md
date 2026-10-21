# Research Intelligence Assistant
**Live Demo:** [https://multi-agent-research-assistant-hmcd5iedk.vercel.app/](https://multi-agent-research-assistant-hmcd5iedk.vercel.app/)
A research workspace that retrieves scholarly literature, grounds claims in evidence, compares findings across papers, and produces a traceable research report through a controlled LangGraph workflow.

## Overview

Research Intelligence Assistant is a full-stack research system built around an evidence-oriented pipeline rather than a simple question-and-answer interface.

A research request is processed through query planning and scholarly search, paper deduplication/ranking, document chunking, semantic evidence retrieval, claim validation, evidence-support verification, cross-paper comparison, contradiction analysis, research-gap identification, bounded iterative research, grounded synthesis, and citation validation.

The system also includes application infrastructure around the research workflow: authenticated users, PostgreSQL persistence, LangGraph checkpointing, asynchronous research jobs, Server-Sent Events (SSE), rate limiting, structured logging, database migrations, and a React research workspace.

The implementation deliberately distinguishes evidence retrieval from research intelligence. Retrieved papers provide the source material; downstream components reason over claims, evidence, methodologies, agreements, contradictions, and gaps instead of treating an LLM response as sufficient evidence.

## Key Features

- **Scholarly retrieval** using the repository's search providers, including ArXiv-based retrieval.
- **Query rewriting and planning** before scholarly search.
- **Document chunking and semantic evidence retrieval** using ChromaDB and embeddings.
- **Claim extraction and validation** with explicit evidence relationships.
- **Evidence-support verification** to determine whether claims are supported by retrieved material.
- **Cross-paper research intelligence** covering study comparisons, consensus, contradictions, evidence strength, and research gaps.
- **Provenance validation** linking findings back through claims, evidence, papers, chunks, and source text.
- **Controlled agentic research loop** with limits on iterations, searches, cumulative papers/evidence, research-call budgets, drift, and stopping conditions.
- **Deterministic citation generation** for supported citation formats.
- **Grounded report generation** with structured research sections.
- **Asynchronous research jobs** with explicit `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED` lifecycle states.
- **Server-Sent Events** for live research progress and agent trace updates, with polling recovery.
- **JWT authentication** with password hashing, token revocation, and server-side resource ownership checks.
- **Multi-user isolation** for sessions, jobs, and reports.
- **PostgreSQL persistence** through SQLAlchemy and Alembic migrations.
- **PostgreSQL-backed LangGraph checkpointing**, with SQLite fallback for local development.
- **Operational controls** including rate limiting, request/body limits, security headers, correlation IDs, structured logging, health checks, and sanitized exception handling.
- **React research workspace** exposing research brief, findings and claims, evidence, sources, contradictions, methodology, research gaps, and research trace.

## System Architecture

```mermaid
flowchart LR
    U[Researcher] --> FE[React / Vite Workspace]

    FE --> AUTH[JWT Authentication]
    FE --> API[FastAPI API]

    API --> JOB[Research Job Manager]
    API --> DB[(PostgreSQL)]
    API --> SSE[SSE Job Stream]

    JOB --> GRAPH[LangGraph Research Graph]

    GRAPH --> SUP[Supervisor]
    SUP --> SEARCH[Search / Query Rewrite]
    SEARCH --> RET[Scholarly Retrieval]
    RET --> RAG[Chunking + Evidence Retrieval]
    RAG --> CLAIMS[Claim Validation + Support Verification]
    CLAIMS --> INTEL[Cross-Paper Intelligence]
    INTEL --> LOOP[Controlled Research Loop]
    LOOP -->|evidence insufficient| SEARCH
    LOOP -->|sufficient / stop| SYN[Grounded Synthesis]
    SYN --> CIT[Citation Validation]
    CIT --> REPORT[Research Report]

    RET --> CHROMA[(ChromaDB)]
    RAG --> CHROMA
    GRAPH --> CP[(PostgreSQL LangGraph Checkpoints)]

    REPORT --> DB
    GRAPH --> SSE
    SSE --> FE
```

### Major Components

**Frontend**

The React/Vite application provides the authenticated research workspace and consumes the backend's asynchronous job and SSE interfaces.

**FastAPI API**

The backend exposes authentication, research, job, session, streaming, health, and metrics functionality. Research requests are submitted as background jobs rather than keeping the normal HTTP request open for the complete research process.

**LangGraph orchestration**

The research workflow is represented as a stateful graph. The graph coordinates retrieval, evidence processing, intelligence generation, report construction, and controlled iterative research.

**Search and RAG**

Search providers retrieve scholarly material. Documents are chunked and indexed in ChromaDB so downstream components can retrieve semantically relevant evidence.

**Research intelligence**

The intelligence layer compares studies rather than merely summarizing them. It classifies agreement and contradiction conditions, evaluates evidence strength, identifies evidence-grounded research gaps, and preserves provenance.

**Persistence**

PostgreSQL stores durable application state. LangGraph checkpoints are persisted through PostgreSQL in production. Alembic manages relational schema migrations.

## System Workflow

```text
Research Query
      ↓
Authentication / Request Validation
      ↓
Async Research Job
      ↓
Query Planning / Rewriting
      ↓
Scholarly Search
      ↓
Deduplication + Ranking
      ↓
Document Chunking
      ↓
Semantic Evidence Retrieval
      ↓
Claim Extraction + Validation
      ↓
Evidence Support Verification
      ↓
Cross-Paper Comparison
      ↓
Consensus / Contradiction Analysis
      ↓
Research Gap Identification
      ↓
Controlled Agentic Loop
      ├── insufficient evidence → additional bounded research
      └── sufficient / stopping condition → continue
      ↓
Grounded Synthesis
      ↓
Citation / Provenance Validation
      ↓
Persisted Research Report
      ↓
SSE / Polling → React Workspace
```

### Active research orchestration

The authoritative graph is implemented in `app/graph/research_graph.py`.

The current workflow is organized around the following logical stages:

```text
supervisor
   ↓
search
   ↓
rag / evidence processing
   ↓
summary
   ↓
citation
   ↓
intelligence
   ↓
report
   ↓
END
```

The later-stage implementation extends the graph state with evidence, claims, cross-paper findings, study comparisons, contradiction findings, evidence strength, research gaps, consensus synthesis, and compatibility fields used by the reporting layer.

The repository also contains additional agent, loop, and intelligence modules. Their presence in the source tree should not be interpreted as independent execution paths: the authoritative graph and the job execution path determine what actually runs.

## Technical Architecture

### Backend

The backend uses FastAPI with Pydantic schemas and SQLAlchemy-backed persistence. Long-running research requests are represented by durable job records and executed through the job manager.

The job layer provides:

- explicit lifecycle states;
- per-user and global concurrency limits;
- duplicate-job protection;
- cooperative cancellation;
- error metadata;
- duration tracking;
- progress state;
- recovery handling for stale jobs.

### Agent orchestration

LangGraph provides stateful orchestration and checkpointing. Research state is passed between graph nodes instead of being reconstructed independently by each API request.

The controlled loop prevents unrestricted autonomous execution through configuration such as:

- maximum research iterations;
- maximum searches per iteration;
- cumulative paper limits;
- cumulative evidence limits;
- research-call budgets;
- query-drift controls;
- evidence-sufficiency checks;
- stopping conditions.

### Retrieval and evidence

The retrieval layer separates source discovery from evidence selection. Retrieved scholarly documents are chunked and indexed in ChromaDB. Evidence objects carry identifiers and provenance relationships used by downstream validation and research-intelligence components.

The repository intentionally avoids inventing missing methodology details. If retrieved literature does not expose a value such as a sample size or baseline, the system can preserve that information as unavailable rather than infer it.

### Research intelligence

The intelligence layer operates across retrieved studies and can produce:

- cross-paper findings;
- study comparisons;
- contradiction findings;
- evidence-strength classifications;
- consensus synthesis;
- research gaps.

Evidence strength is represented through interpretable classifications such as `INSUFFICIENT`, `MIXED`, `LIMITED`, `MODERATE`, and `STRONG` rather than unsupported percentage confidence scores.

Research gaps are scoped to the retrieved literature rather than presented as claims about the entire scientific literature.

### Provenance

The provenance layer maintains a chain conceptually represented as:

```text
Research Finding
    ↓
Claim ID
    ↓
Evidence ID
    ↓
Paper ID
    ↓
Chunk ID
    ↓
Source Text
```

Findings that reference invalid or phantom evidence identifiers can be rejected before promotion into the final report.

### Persistence

The relational database contains durable entities including:

- users;
- research sessions;
- research runs;
- research iterations;
- research jobs;
- reports;
- revoked tokens.

SQLAlchemy manages application persistence, while Alembic manages schema migrations.

LangGraph checkpoint persistence uses PostgreSQL in production. Local development can use the configured SQLite fallback.

### Authentication and isolation

Authentication uses signed JWT access tokens and hashed passwords.

User-owned resources carry user ownership information, and server-side authorization checks prevent users from accessing another user's sessions, jobs, reports, or job streams.

### Streaming

Research execution events are published through Server-Sent Events. The frontend subscribes to a job-specific stream and also supports polling recovery.

### Reliability and security controls

The backend includes:

- request validation;
- CORS configuration;
- rate limiting;
- request/body size limits;
- security headers;
- structured logging;
- correlation IDs;
- secret sanitization in logs;
- typed application exceptions;
- sanitized error responses;
- health checks;
- database transaction handling.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python | Backend and research workflow implementation |
| API | FastAPI | HTTP API and application service |
| Validation | Pydantic / Pydantic Settings | Request and configuration validation |
| Agent Orchestration | LangGraph | Stateful research workflow and checkpointing |
| LLM | Google Gemini | Query processing, research synthesis, and agent tasks |
| Retrieval | ChromaDB | Vector storage and semantic evidence retrieval |
| Embeddings | Google embedding integration | Semantic representation of research chunks |
| Database | PostgreSQL | Durable application state and production checkpoints |
| ORM | SQLAlchemy | Relational persistence |
| Migrations | Alembic | Database schema versioning |
| Authentication | JWT / password hashing | User authentication and authorization |
| Background Execution | Python job manager / ThreadPoolExecutor | Asynchronous research execution |
| Streaming | Server-Sent Events | Research progress and trace updates |
| Frontend | React | Research workspace |
| Frontend Build | Vite | Frontend development and production builds |
| Styling | Tailwind CSS | Workspace styling |
| Containerization | Docker / Docker Compose | Containerized development and deployment |
| Deployment | Render / Vercel | Backend and frontend hosting |

## Repository Structure

```text
Research-Intelligence-Assistant/
├── app/
│   ├── agents/          # Specialized research agents
│   ├── api/             # API routes, schemas, streaming
│   ├── auth/            # Authentication and authorization
│   ├── core/            # Configuration, logging, metrics, rate limiting
│   ├── db/              # Database sessions, models, checkpoints
│   ├── graph/           # LangGraph research orchestration
│   ├── intelligence/    # Cross-paper intelligence and provenance
│   ├── jobs/            # Background job execution
│   ├── loop/            # Controlled research-loop components
│   ├── memory/          # Research/session memory
│   ├── models/          # Domain and state models
│   ├── rag/             # Chunking, embeddings, evidence retrieval
│   ├── search/          # Search providers, ranking, deduplication
│   ├── services/        # LLM and application services
│   └── utils/           # Parsing, retry, logging, execution utilities
├── frontend/            # React/Vite research workspace
├── evaluation/          # Evaluation and quality-gate infrastructure
├── tests/               # Backend and production-oriented tests
├── alembic/             # Database migration configuration and versions
├── scripts/             # Operational utilities
├── docs/                # Architecture, security, stage, and release docs
├── Dockerfile
├── docker-compose.yml
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

The `docs/v2/` directory is historical development documentation for the current repository. It describes the engineering stages used to build and harden the project; it is not a separate product.

## Installation

### Prerequisites

- Python environment compatible with the versions supported by the dependency set.
- Node.js and npm for the frontend.
- PostgreSQL for production-style local execution.
- A Google Gemini API key for LLM-backed research.
- Git.

### Clone

```bash
git clone https://github.com/JogiRohithKumar/Research-Intelligence-Assistant.git
cd Research-Intelligence-Assistant
```

### Backend environment

Create a virtual environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Database

For a PostgreSQL-backed local environment, configure `DATABASE_URL` and run:

```bash
alembic upgrade head
```

The application also contains an explicit SQLite fallback for local development when configured.

### Frontend

```bash
cd frontend
npm install
```

## Environment Variables

Use `.env.example` as the configuration reference. Do not commit `.env` or production secrets.

### Required for research

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### Production database

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
```

### Production authentication

```env
JWT_SECRET_KEY=replace_with_a_random_secret_at_least_32_characters
ENV=production
DEBUG=false
```

### Other configuration

The application configuration also supports settings for:

```env
GEMINI_MODEL=gemini-2.5-flash
GEMINI_FAST_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004

AUTH_ENABLED=true

RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=10/minute
RATE_LIMIT_RESEARCH=5/minute

DATABASE_FALLBACK_SQLITE=true
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

CORS_ORIGINS=...
CORS_ORIGIN_REGEX=...
```

Values should be adapted to the deployment environment. Production safety validation rejects insecure database/authentication configurations such as SQLite as the production database, development debug mode, insecure/default JWT secrets, and disabled authentication.

## Running the Project

### Backend

From the repository root:

```bash
uvicorn main:app --reload
```

The deployed backend uses the same FastAPI application entry point with Uvicorn.

### Frontend

In another terminal:

```bash
cd frontend
npm run dev
```

The frontend uses the configured API URL to communicate with the backend.

### Docker

The repository also contains `Dockerfile` and `docker-compose.yml` for containerized environments.

## Usage

### Web application

The normal workflow is:

1. Open the React workspace.
2. Register or sign in.
3. Enter a scholarly research question.
4. Submit the research request.
5. The frontend creates an asynchronous research job.
6. Follow progress through SSE events and polling recovery.
7. Inspect the resulting research workspace.
8. Review the research brief, findings, claims, evidence, sources, contradictions, methodology, research gaps, and research trace.

### API

The backend exposes an asynchronous research interface centered around:

```http
POST /research
```

A submitted research request returns a job-oriented workflow rather than requiring the HTTP request to remain open until the entire research pipeline completes.

Job status is available through:

```http
GET /jobs/{job_id}
```

Active jobs can be cancelled through:

```http
POST /jobs/{job_id}/cancel
```

Authentication routes include:

```http
POST /auth/register
POST /auth/login
GET  /auth/me
POST /auth/logout
```

The API also exposes session-oriented routes and metrics functionality.

### Health check

```bash
curl -i http://localhost:8000/health
```

A healthy deployment reports the application status, environment, and database configuration state.

## Screenshots / Demo

The repository contains a React research workspace, but this README does not embed screenshots that are not maintained as repository assets.

The deployed frontend and backend can be used as the current demonstration environment when available.

## API Reference

The API is organized around authentication, research execution, sessions, jobs, streaming, health, and metrics.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Register a user |
| `POST` | `/auth/login` | Authenticate and obtain access credentials |
| `GET` | `/auth/me` | Return the authenticated user |
| `POST` | `/auth/logout` | Revoke/logout the current token |
| `POST` | `/research` | Submit a research job |
| `GET` | `/jobs/{job_id}` | Retrieve job state |
| `POST` | `/jobs/{job_id}/cancel` | Request job cancellation |
| `GET` | `/health` | Service health check |
| `GET` | `/metrics` | Application metrics |
| `GET/POST/DELETE` | `/sessions/...` | Research session operations |
| `GET` | Job stream endpoint | Subscribe to authenticated job events over SSE |

Exact request and response schemas are defined in `app/api/schemas.py` and the route implementations under `app/api/`.

## Testing

The repository contains tests covering the research system and production engineering layers, including:

```text
tests/
├── test_foundation.py
├── test_search_retrieval.py
├── test_rag_evidence.py
├── test_stage4_intelligence.py
├── test_stage5_agentic_loop.py
├── test_stage7_production.py
└── test_production_e2e_smoke.py
```

The test suite covers areas such as:

- retrieval behavior;
- RAG and evidence handling;
- claim and citation behavior;
- cross-paper research intelligence;
- contradiction detection;
- research-gap detection;
- controlled agentic-loop behavior;
- authentication and authorization;
- user/resource isolation;
- asynchronous job execution;
- cancellation;
- database persistence;
- graph execution;
- production smoke behavior.

Run the backend tests with:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The repository also contains frontend workspace tests.

## Limitations

- **External model dependency:** Research generation depends on the configured Google Gemini API and its quotas, rate limits, availability, and model behavior.
- **Scholarly corpus boundary:** Conclusions, contradictions, and research gaps are relative to the literature retrieved for a given research request; they are not claims about every paper ever published.
- **Abstract-level evidence:** The current search pipeline primarily works from retrieved scholarly metadata and abstract-level material. Full-text PDF table/figure extraction is not the basis of the current workflow.
- **Missing methodology remains missing:** The system does not infer unavailable methodological values simply to complete a report.
- **Vector-store scope:** ChromaDB is part of the retrieval/evidence architecture, but the exact corpus available to a research run depends on the documents retrieved and indexed during execution.
- **LLM call budget:** The controlled research loop intentionally limits model/search activity. This constrains execution cost and duration but can also limit additional evidence discovery.
- **Free-tier API quotas:** Development or low-cost deployments using free model/API quotas can fail or stall research jobs when the provider quota is exhausted.
- **Background execution model:** The current job manager uses in-process background execution rather than a distributed queue such as Celery/Redis. This is a deliberate implementation constraint and affects horizontal execution semantics.
- **SSE is connection-oriented:** Real-time updates depend on the browser maintaining the event-stream connection; polling recovery exists as a fallback.
- **Deployment is multi-service:** The frontend and backend are deployed separately and require consistent API/CORS configuration.

## Future Improvements

- Replace in-process background execution with a durable distributed worker/queue architecture for larger multi-instance deployments.
- Expand scholarly providers beyond the currently implemented providers and improve provider-specific ranking strategies.
- Add full-text document ingestion and PDF-level evidence extraction for papers where full text is legally and technically available.
- Add stronger automated evaluation around retrieval quality, evidence recall, claim support, and end-to-end report quality.
- Move vector retrieval to a shared production vector infrastructure when corpus size and deployment topology require it.
- Add more explicit resource-aware budgeting across search calls, embedding operations, and LLM calls.
- Improve frontend observability around failed jobs and provider quota exhaustion.

## License

No license file is currently documented in the repository. Unless a license is added, the source should not be assumed to be available for unrestricted redistribution or reuse.
