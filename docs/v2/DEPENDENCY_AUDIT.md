# DEPENDENCY SECURITY & AUDIT REPORT
**Project:** Research-Intelligence-Assistant V2  
**Date:** 2026-10-05  
**Stage:** Stage 1 — Foundation & Architecture (Security Gate)  
**Status:** AUDITED  

---

## 1. Executive Summary

This report establishes the dependency security baseline across Python backend packages and Node/npm frontend dependencies. The audit identifies direct dependencies, transitive packages, unused dependencies, duplicate SDKs, outdated libraries, and reported vulnerabilities.

Per Stage 1 rules, packages are **not blindly removed or upgraded** without verifying import references and evaluating breaking change risks.

---

## 2. Python Dependencies Audit (`requirements.txt`)

### Direct Dependencies Inventory

| Package | Current Version | Status | Purpose in V2 | Vulnerability / Advisory Status |
| :--- | :--- | :--- | :--- | :--- |
| `fastapi` | 0.136.3 | **Required** | Core ASGI web framework and API routing | No known critical CVEs |
| `uvicorn` | 0.49.0 | **Required** | High-performance ASGI production server | No known critical CVEs |
| `pydantic` | 2.13.4 | **Required** | Data validation, domain schemas, settings | No known critical CVEs |
| `pydantic-settings` | 2.14.1 | **Required** | Centralized BaseSettings environment config | Missing from legacy `requirements.txt` |
| `google-genai` | 2.8.0 | **Required** | Modern, official Google Gemini SDK | Clean; current official SDK |
| `google-generativeai` | 0.8.6 | **Deprecated / Duplicate** | Legacy Gemini SDK | Deprecated by Google; unmaintained |
| `langgraph` | 1.2.5 | **Required** | Core multi-agent state orchestration graph | No known critical CVEs |
| `langgraph-checkpoint-sqlite` | 3.1.0 | **Required** | SQLite state persistence checkpointer | No known critical CVEs |
| `langchain` | 1.3.9 | **Unused Candidate** | Umbrella LangChain package | No direct imports in `app/` |
| `langchain-core` | 1.4.7 | **Transitive Dependency** | Required transitively by LangGraph | Transitive dependency |
| `langchain-google-genai` | 4.2.5 | **Unused Candidate** | LangChain wrapper for Gemini | Zero imports in `app/` |
| `chromadb` | 1.5.9 | **Required** | Embedded vector database for paper retrieval | No known critical CVEs |
| `requests` | 2.34.2 | **Required** | HTTP client for arXiv Atom API queries | No known critical CVEs |
| `python-dotenv` | 1.2.2 | **Required** | Environment variable file loading | No known critical CVEs |

### Proposed Python Removals & Replacements

#### Proposed Action 1: Remove `google-generativeai`
- **Package:** `google-generativeai`
- **Reason:** Upstream Google has completely ended maintenance and support for `google-generativeai`. Emits runtime `FutureWarning` on every import.
- **Evidence:** Grep across `app/` confirms 0 imports remain after Stage 1 refactored all LLM logic to `google-genai` in `app/services/llm_service.py`.
- **Risk:** Low. No active code imports this module.
- **Decision:** Remove from `requirements.txt` in Stage 1 / Stage 7. Retain in `.venv-2` until formal cutover to avoid unexpected downstream breaks.

#### Proposed Action 2: Remove `langchain` and `langchain-google-genai`
- **Package:** `langchain`, `langchain-google-genai`
- **Reason:** Unused umbrella dependencies. `langgraph` depends directly on `langchain-core` rather than the bloated monolithic `langchain` package.
- **Evidence:** Grep across `app/` confirms zero occurrences of `import langchain` or `import langchain_google_genai`.
- **Risk:** Very low. `langgraph` runs independently using its own prebuilts and `langchain-core`.
- **Decision:** Safe candidate for pruning in `requirements.txt` in Stage 7.

#### Proposed Action 3: Add `pydantic-settings` to `requirements.txt`
- **Package:** `pydantic-settings`
- **Reason:** Core dependency utilized by `app/core/config.py`. Installed in `.venv-2` but omitted from legacy `requirements.txt`.
- **Evidence:** `app/core/config.py` imports `from pydantic_settings import BaseSettings, SettingsConfigDict`.
- **Risk:** Omitting it breaks container or clean virtual environment setups.
- **Decision:** Add to `requirements.txt` immediately.

---

## 3. Frontend Dependencies Audit (`frontend/package.json`)

### Direct Dependencies Inventory

| Package | Specified Version | Status | Purpose | Vulnerabilities (npm audit) |
| :--- | :--- | :--- | :--- | :--- |
| `react` | ^18.3.1 | **Required** | Core UI library | 0 vulnerabilities |
| `react-dom` | ^18.3.1 | **Required** | React DOM rendering | 0 vulnerabilities |
| `lucide-react` | ^0.468.0 | **Required** | Modern SVG icons | 0 vulnerabilities |
| `axios` | ^1.7.9 | **Unused Candidate / High Risk** | Unused HTTP client wrapper | **22 High-Severity Vulnerabilities** (Prototype pollution, ReDoS, SSRF) |
| `vite` | ^8.0.0 | **Required** (dev) | Frontend bundler & dev server | 0 vulnerabilities |
| `tailwindcss` | ^3.4.16 | **Required** (dev) | CSS styling framework | Transitive high severity via `braces`/`chokidar` |
| `postcss` | ^8.4.49 | **Required** (dev) | CSS post-processing | Transitive high severity in build chain |
| `autoprefixer` | ^10.4.20 | **Required** (dev) | CSS vendor prefixing | 0 vulnerabilities |

### Proposed npm Removals & Upgrades

#### Proposed Action 1: Remove `axios` from frontend
- **Package:** `axios`
- **Reason:** Contains 22 high-severity vulnerabilities (GHSA-xj6q-8x83-jv6g, GHSA-mmx7-hfxf-jppx, etc.). The frontend `App.jsx` already uses native browser `fetch()`. `frontend/src/services/api.js` was disconnected legacy dead code.
- **Evidence:** `App.jsx` executes all requests via `window.fetch`. `api.js` is not imported anywhere in the component tree.
- **Risk:** Zero risk to running application. Eliminates all 22 high-severity Axios security alerts from client code.
- **Decision:** Remove `axios` from `package.json` in Stage 6 / Stage 7.

#### Proposed Action 2: Upgrade TailwindCSS / Chokidar toolchain
- **Package:** `tailwindcss` 3.4.16 → 4.x / updated patch
- **Reason:** Transitive dependency `braces` has stack exhaustion ReDoS vulnerability (GHSA-vfj7-8cjw-p6xm) via `chokidar` 3.x.
- **Evidence:** Build-time only; not present in client runtime bundle.
- **Risk:** Upgrading to Tailwind v4 is a major breaking change requiring CSS configuration migration.
- **Decision:** Retain current Tailwind 3.4 for Stage 1. Migrate build chain cleanly in Stage 7 (Production Engineering).

---

## 4. Summary Action Table

| Ecosystem | Dependency | Action | Phase Target | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| Python | `pydantic-settings` | **Add** to `requirements.txt` | Stage 1 | Fresh venv install test |
| Python | `google-generativeai` | **Prune** | Stage 7 | Grep & smoke test |
| Python | `langchain` | **Prune** | Stage 7 | Grep & smoke test |
| Python | `langchain-google-genai` | **Prune** | Stage 7 | Grep & smoke test |
| Node/npm | `axios` | **Prune** | Stage 6/7 | `npm uninstall axios` & `npm run build` |
| Node/npm | `braces` / `postcss` | **Patch / Upgrade** | Stage 7 | `npm audit fix` with non-breaking version |
