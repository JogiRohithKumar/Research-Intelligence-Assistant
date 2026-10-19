# V2 SECURITY BASELINE & AUDIT REPORT
**Project:** Research-Intelligence-Assistant V2  
**Date:** 2026-10-05  
**Stage:** Stage 1 — Foundation & Architecture (Security Gate)  
**Standard References:** OWASP API Security Top 10, OWASP ASVS v4.0.3  
**Status:** **STAGE 1 SECURITY GATE COMPLETED**  

---

## 1. Threat Model Summary

Research-Intelligence-Assistant is designed as an internet-facing scholarly intelligence platform. The primary threat actors and vectors considered include:
- **Unauthenticated Internet Attackers:** Resource exhaustion (DoS) via uncontrolled expensive research and LLM generation runs; prototype pollution / XSS via untrusted external literature metadata; parameter tampering on `thread_id` / `session_id`.
- **Eavesdroppers / MITM:** Interception of client-backend or backend-LLM communication; leakage of credentials or sensitive research queries in transit.
- **Supply-Chain & Dependency Attacks:** Vulnerabilities in third-party Python packages or npm libraries leading to remote code execution or denial of service.
- **Malicious External Content:** Indirect prompt injection embedded within scientific abstracts or paper metadata retrieved from third-party repositories.

---

## 2. Protected Assets

| Asset | Classification | Storage Location | Protection Requirements |
| :--- | :--- | :--- | :--- |
| **Google Gemini API Key** | High Secret | Server-side `.env` / Environment | NEVER exposed to browser, git, or client bundles. |
| **User Research Queries** | Confidential | SQLite Checkpoint / Memory | Protected against cross-tenant snooping. |
| **Synthesized Intelligence Reports** | Intellectual Property | SQLite Checkpoint / Memory | Scoped by tenant/session ID. |
| **Vector Embeddings & Chunks** | Internal Data | Local ChromaDB (`app/db/chroma`) | Protected from arbitrary direct file downloads. |
| **System Event & Audit Logs** | Operational Data | Memory / Local log files | Sanitized of credentials, tokens, and PII. |

---

## 3. Trust Boundaries

```
[Untrusted Web Browser]
         │
         │  TLS (HTTPS) + Input Validation + Origin Checks
         ▼
[Trust Boundary 1: FastAPI API Gateway]
         │
         │  Internal Application Context & Sanitization
         ▼
[Trust Boundary 2: LangGraph Orchestrator & Local Persistence]
         │
         │  Outbound TLS + Server-Side Secrets Only
         ▼
[External Services: Google Gemini API & arXiv Atom API]
```

- **Client-to-Gateway:** Public and semi-trusted. All inputs must be strictly validated before touching graph or model layers.
- **Gateway-to-Services:** High-trust internal boundary. External API keys are kept strictly on the backend.
- **External API Responses:** Untrusted. Data retrieved from arXiv or parsed from LLMs must be schema-validated before rendering or ingestion.

---

## 4. Authentication Model

- **Current Status:** **PARTIAL** (Stage 1 Foundation)
- **Current Mechanism:** 
  - Machine-level API key authorization implemented in `app/auth/auth.py` via `x-api-key` header checked against `settings.ALLOWED_API_KEYS`.
  - In development mode (`settings.API_KEY_ENABLED=False`), requests are permitted to facilitate automated local smoke testing.
  - Hardcoded legacy key (`research-assistant-demo-key`) has been completely eradicated from backend and frontend source trees.
- **User Authentication:** **NOT IMPLEMENTED (DEFERRED TO STAGE 7)**. User accounts, JWT/OAuth2 tokens, passwords, and user session lifecycles belong to Stage 7 (Production Engineering).

---

## 5. Authorization Model & Endpoint Matrix

- **Current Status:** **PARTIAL**

### Endpoint Authorization Matrix

| Endpoint | Method | Authentication Required? | Authorization Required? | Object Ownership Checked? | Admin Only? | Rate Limited? | Stage 1 Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/health` | `GET` | No | No (Public) | N/A | No | No | **PASS** |
| `/research` | `POST` | If `API_KEY_ENABLED` | Machine API Key | **DEFERRED TO STAGE 7** | No | **DEFERRED TO STAGE 7** | **PARTIAL** |
| `/stream` | `GET` | No | No (Public legacy) | **DEFERRED TO STAGE 7** | No | **DEFERRED TO STAGE 7** | **PARTIAL** |

- **ID Parameter Auditing:**
  - `thread_id`: Previously bound to raw `request.query`. Now generated with unique cryptographic hash and timestamp (`thread_{query_hash}_{timestamp}`) to prevent cross-run state collisions.
  - Multi-user object-level access control (validating that the requesting user owns `thread_id` or `session_id`) is **DEFERRED TO STAGE 7**.

---

## 6. Secret Management

- **Current Status:** **PASS**
- **Server-Side Secrets:** `GEMINI_API_KEY` is loaded strictly on the backend using Pydantic `BaseSettings` (`app/core/config.py`).
- **Frontend Architecture:** 
  - Removed `VITE_API_KEY` and `'x-api-key'` headers entirely from `frontend/src/App.jsx`.
  - Frontend only knows `VITE_API_URL`.
  - Verified by scanning `dist/assets/index-*.js`: ZERO secrets or API keys are present in client bundles.
- **Environment Example:** Created `.env.example` with placeholder strings only (`your_gemini_api_key_here`).

---

## 7. Input Validation & Resource Exhaustion Controls

- **Current Status:** **PASS** (Stage 1 Baseline)
- **Controls Implemented:**
  - `query`: Minimum length 2 characters, maximum length 1,000 characters enforced via Pydantic `Field(min_length=2, max_length=1000)`.
  - `session_id`: Alphanumeric regex enforced (`^[a-zA-Z0-9_\-]+$`), maximum length 128 characters.
  - Rejection of oversized payloads prevents uncontrolled token consumption and memory denial-of-service.

---

## 8. XSS Protections

- **Current Status:** **PASS**
- **Frontend Sinks Inspected:**
  - `dangerouslySetInnerHTML`: Zero usages across all components in `frontend/src`.
  - React auto-escaping handles `{report.summary}`, `{item}`, and `{paper.title}`.
  - External Paper Links: In `App.jsx`, links are strictly protocol-validated with `/^https?:\/\//i` to neutralize `javascript:` URI execution vectors.

---

## 9. CORS Policy

- **Current Status:** **PASS** (Development Hardened)
- **Configuration (`main.py`):**
  - Explicit allowed origins: `settings.CORS_ORIGINS` (`http://localhost:5173`, `http://127.0.0.1:5173`, etc.).
  - Regex pattern: Restricted to `https://multi-agent-research-assistant-.*\.vercel\.app`.
  - Methods: Whitelisted explicitly to `["GET", "POST", "OPTIONS"]`.
  - Headers: Whitelisted explicitly to `["Content-Type", "x-api-key", "Authorization"]`.
  - Wildcard `*` origins with credentials are NOT permitted.

---

## 10. Security Headers

- **Current Status:** **PASS**
- **Middleware Implemented in `main.py`:**
  - `X-Content-Type-Options: nosniff` (Active)
  - `X-Frame-Options: DENY` (Active)
  - `Referrer-Policy: strict-origin-when-cross-origin` (Active)
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()` (Active)
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (Active in production mode)

---

## 11. Rate Limiting

- **Current Status:** **NOT IMPLEMENTED (DEFERRED TO STAGE 7)**
- **Requirement for Stage 7:**
  - Implement token-bucket or sliding-window rate limiting on `/research` (e.g., 5 requests/minute per IP/tenant) using Redis or in-memory limiter (`slowapi`) to mitigate API cost exhaustion.

---

## 12. Dependency Security

- **Current Status:** **PASS** (Audit Documented)
- **Documentation:** Full audit published in `docs/v2/DEPENDENCY_AUDIT.md`.
- **Key Findings:**
  - Python: Missing `pydantic-settings` added to `requirements.txt`. Deprecated `google-generativeai` and unused `langchain` flagged for pruning.
  - Node/npm: `axios` identified as having 22 high-severity vulnerabilities; scheduled for complete removal in Stage 6/7 as frontend already uses native `fetch()`.

---

## 13. Database Security

- **Current Status:** **PASS** (Stage 1 Scope)
- **Findings:**
  - SQLite database (`app/db/research.db`) is stored locally; absolute path resolved; ignored by `.gitignore`.
  - ChromaDB (`app/db/chroma/`) is stored locally; ignored by `.gitignore`.
  - No static file routes serve `.db` or vector store files.
  - Multi-tenant data segregation and PostgreSQL migration are **DEFERRED TO STAGE 7**.

---

## 14. Logging & Secret Sanitization

- **Current Status:** **PASS**
- **Implementation (`app/core/logging.py`):**
  - Integrated `SecretSanitizingFormatter` with regex filters targeting Google API keys (`AIzaSy...`), `GEMINI_API_KEY`, and `x-api-key`.
  - Scrubbed secrets replaced with `***REDACTED***`.
  - Stack traces sanitized via standardized domain exception handlers.

---

## 15. File Exposure Audit

- **Current Status:** **PASS**
- **Hardened `.gitignore`:**
  - Added comprehensive ignore blocks for `.env`, `.env.*`, `*.pem`, `*.key`, `*.db`, `*.sqlite*`, `.venv*/`, `logs.jsonl`, `*.log`, `scratch/`.
  - Confirmed via `git ls-files` that no database files, environment variables, or private keys are tracked.

---

## 16. Third-Party API Security

- **Current Status:** **PASS**
- **Google Gemini API:**
  - TLS 1.3 enforced by `google-genai`.
  - Server-side credentials only.
  - Output validation through Pydantic schemas prevents prompt injection effects from propagating.
- **arXiv Atom API:**
  - Queries routed over HTTPS/HTTP with 30s timeouts.
  - URL is strictly hardcoded to `export.arxiv.org` (no user-controlled target SSRF).

---

## 17. Git Secret Scanning

- **Current Status:** **PASS** (Legacy Findings Documented)
- **Scan Scope:** All 12 commits in repository history.
- **Historical Findings:**
  - Commits `b15dbdb` and `4bdea87` contained plaintext demo token `research-assistant-demo-key` in `app/auth/api_keys.py` and `frontend/src/App.jsx`.
  - ZERO Google/Gemini API keys, private keys, or production secrets were ever committed to Git history.
- **Current Tree:** Clean. Zero unredacted keys present.

---

## 18. Production Security Requirements (Locked for Launch)

1. Mandatory HTTPS enforcement across all endpoints.
2. Custom domain with managed TLS certificates.
3. Production environment flags (`ENV=production`, `DEBUG=false`).
4. Complete removal of debug endpoints, sourcemaps, and fallback test tokens.
5. Mandatory legal compliance: Privacy Policy and Terms of Service.

---

## 19. Deferred Stage 7 Security Work

- Multi-tenant user authentication (JWT / OAuth2 / bcrypt or Argon2id password hashing).
- Object-level authorization (verifying ownership of `thread_id` and `session_id`).
- Per-tenant rate limiting and resource throttling on `/research`.
- True Server-Sent Events (SSE) streaming per authenticated connection.
- PostgreSQL migration and database connection pooling.
- Pruning of vulnerable `axios` package from frontend `package.json`.

---

## 20. Stage 8 Security Testing Requirements

- Automated DAST (Dynamic Application Security Testing) scanning against API endpoints.
- Fuzz testing against arXiv XML parsing and LLM structured output schemas.
- Adversarial prompt injection evaluation (testing prompt resistance against indirect injection in research papers).
- Dependency vulnerability gate in CI/CD pipeline (`pip-audit`, `npm audit`).
