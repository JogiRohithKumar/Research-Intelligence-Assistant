# STAGE 2: RESEARCH SEARCH & RETRIEVAL ENGINE SPECIFICATION

**Rebuild Phase:** Stage 2 of 9  
**Status:** COMPLETE & VERIFIED  
**Target Module:** `app/search/`, `app/rag/`, `app/agents/search_agent.py`  
**Boundary:** Prepares normalized candidate papers and indexed vector store context for Stage 3 RAG. Does NOT implement evidence quote grounding or sentence claim citations.

---

## 1. Current Architecture Overview

Stage 2 replaces the legacy naive search implementation (which relied on single unvalidated arXiv queries, hardcoded AI keywords, and unqueried vector storage) with a modular, query-driven research search and retrieval engine.

```
USER QUERY
    │
    ▼
QUERY PLANNER (app/search/query_planner.py)
    │  - Normalizes text and strips punctuation
    │  - Generates primary query & variants (capped at MAX_SEARCH_VARIANTS)
    │  - Extracts key technical concepts
    │  - Defines scholarly research intent
    ▼
SEARCH PLAN (SearchPlan)
    │
    ├──► ArxivSearchProvider (app/search/arxiv_provider.py) ──┐
    └──► LocalCorpusProvider (app/search/local_provider.py)  ──┤
                                                               │
                                                               ▼
                                              CANDIDATE COLLECTION (Bounded by MAX_TOTAL_CANDIDATES)
                                                               │
                                                               ▼
                                              DEDUPLICATOR (app/search/deduplication.py)
                                                               │  - DOI resolution (prefix-agnostic)
                                                               │  - Provider ID resolution (arXiv version stripping)
                                                               │  - URL normalization (scheme, format canonicalization)
                                                               │  - Title + Author/Year fallback (distance checks)
                                                               ▼
                                              QUERY-DEPENDENT RANKER (app/search/ranker.py)
                                                               │  - Title coverage (weight: 0.45)
                                                               │  - Abstract coverage (weight: 0.30)
                                                               │  - Concept overlap (weight: 0.15)
                                                               │  - Exact phrase bonus (0.20)
                                                               │  - Recency factor (0.05)
                                                               │  - Metadata completeness (0.05)
                                                               │  - Zero overlap -> strictly 0.0
                                                               ▼
                                              RETRIEVAL SET (NormalizedPaper[])
                                                               │  (Top MAX_FINAL_RETRIEVAL_PAPERS)
                                                               ▼
                                              VECTOR STORE & RETRIEVER (app/rag/)
                                                               │  - Sentence-aware overlapping chunker
                                                               │  - Deterministic chunk IDs: paper:{id}:chunk:{idx}_{hash}
                                                               │  - Enriched metadata preservation in ChromaDB
                                                               │  - Genuine vector retrieval querying ChromaDB
                                                               ▼
                                              STAGE 3 EVIDENCE PIPELINE INTERFACE
```

---

## 2. Query Planning (`app/search/query_planner.py`)

A single, authoritative source of truth for query decomposition and variant generation:
- **`original_query`**: Verbatim user input string.
- **`normalized_query`**: Lowercased, stripped of non-alphanumeric punctuation and excess whitespace.
- **`primary_query`**: Focused academic query constructed from core technical entities (under 10 words).
- **`alternative_queries`**: 1 to `MAX_SEARCH_VARIANTS` targeted queries addressing domain synonyms and methodological sub-aspects.
- **`key_concepts`**: List of 3–6 extracted domain terms/entities.
- **`intent`**: Categorization (e.g. `scholarly_literature_review`, `empirical_evaluation`).
- **Resilience**: Uses Gemini structured output via `google-genai` SDK when configured; falls back deterministically to academic token analysis in offline, test, or rate-limited environments.

---

## 3. Search Provider Abstraction (`app/search/base.py`)

Retrieval logic is completely decoupled from any single external database via the `SearchProvider` abstract base class:

```python
class SearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def search(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[NormalizedPaper]: ...
```

### Implemented Providers:
1. **`ArxivSearchProvider` (`app/search/arxiv_provider.py`)**:
   - Direct Atom XML query against official arXiv API.
   - Robust namespace-aware XML parser.
   - Extracts title, abstract, authors, published dates, integer year, DOI (`arxiv:doi`), journal reference (`arxiv:journal_ref`), and PDF URL.
   - Honors timeout (`SEARCH_TIMEOUT_SECONDS = 25`) and custom User-Agent headers.
2. **`LocalCorpusProvider` (`app/search/local_provider.py`)**:
   - Queries the local ChromaDB persistent vector collection.
   - Groups chunk-level matches by `paper_id` into reconstructed `NormalizedPaper` instances.
   - Seamlessly returns `[]` without error if collection is empty or unpopulated.

---

## 4. Canonical Normalized Paper Schema (`NormalizedPaper`)

The contract across all retrieval and downstream stages:
- **`paper_id`**: Canonical unique identifier (e.g. `arxiv:2301.12345`).
- **`title`**: Cleaned, un-truncated publication title.
- **`abstract`**: Complete text summary.
- **`authors`**: List of author full names.
- **`year`**: Integer publication year (or `None`).
- **`published`**: ISO datetime string.
- **`paper_url`**: Direct canonical URL (abstract or PDF).
- **`doi`**: Digital Object Identifier (clean, without URL prefix).
- **`source`**: Retrieval source provider (`arxiv`, `local_corpus`).
- **`source_id`**: Provider-native identifier.
- **`journal_ref`**: Peer-reviewed journal or conference citation string.
- **`relevance_score`**: Query-dependent score in `[0.0, 1.0]`.
- **`ranking_explanation`**: Explainable breakdown string.
- **`provenance`**: Complete audit trace dict (`provider`, `query`, `retrieved_at`, `sources`, etc.).

---

## 5. Deduplication Strategy (`app/search/deduplication.py`)

Duplicate papers frequently arrive from multiple query variants or across local and external databases. Deduplication follows a deterministic 4-stage identity hierarchy:

1. **DOI**: Strips `https://doi.org/`, `http://dx.doi.org/`, `doi:`, lowercases, and compares canonical alphanumeric DOI.
2. **Provider External ID**: Normalizes arXiv IDs, stripping version tags (e.g. `arxiv:2301.12345v1` and `arxiv:2301.12345v2` map to `arxiv:2301.12345`).
3. **Normalized URL**: Strips protocol, `www`, trailing slashes, and translates PDF vs Abstract arXiv paths.
4. **Title + Author/Year Fallback**: Punctuation-stripped lowercase title comparison. Merges only if first author surname matches OR publication year matches, protecting against collisions on generic titles.

### Non-Merge Guarantee:
Genuinely different papers (e.g. "Attention Is All You Need" vs "Attention Is Not All You Need", or papers sharing identical titles across different authors/years) are mathematically guaranteed NOT to merge.

### Metadata Merging:
When a duplicate sighting is confirmed, the record retains the richest available attributes: non-empty DOI, longest abstract, most complete author list, and combines retrieval provenance sources.

---

## 6. Query-Dependent Ranking (`app/search/ranker.py`)

Hardcoded domain keyword bias (e.g. forcing "llm" or "transformer" on biology or physics queries) has been completely removed. Ranking evaluates candidate papers strictly against the active query:

$$\text{Score} = w_{\text{title}} \cdot C_{\text{title}} + w_{\text{abstract}} \cdot C_{\text{abstract}} + w_{\text{concept}} \cdot C_{\text{concept}} + B_{\text{phrase}} + B_{\text{recency}} + B_{\text{meta}}$$

- **Title Token Coverage ($w=0.45$)**: Proportion of query tokens in title.
- **Abstract Token Coverage ($w=0.30$)**: Proportion of query tokens in abstract.
- **Key Concept Overlap ($w=0.15$)**: Matches with planned domain concepts.
- **Exact Phrase Bonus ($+0.20$)**: Presence of multi-token query sequence in title.
- **Recency Bonus ($+0.01$ to $+0.05$)**: Mild sliding boost for work within 2–10 years.
- **Metadata Quality ($+0.01$ to $+0.05$)**: Presence of DOI, full author roster, and comprehensive abstract.
- **Zero Overlap Rule**: If a paper matches zero tokens in title and abstract and no phrase match, its score is strictly $0.0$.
- **No Fake Confidence**: Internal scores are stored as `relevance_score` and explained in `ranking_explanation`. They are never presented as "AI confidence".

---

## 7. Search Limits and Caps

Configurable thresholds in `app/core/config.py`:
- `MAX_SEARCH_VARIANTS = 3`: Maximum alternative query variants executed.
- `MAX_RESULTS_PER_PROVIDER = 15`: Hard limit per provider per query.
- `MAX_TOTAL_CANDIDATES = 30`: Global candidate pool cap before deduplication.
- `MAX_FINAL_RETRIEVAL_PAPERS = 5`: Maximum papers selected for synthesis and downstream RAG.
- `SEARCH_TIMEOUT_SECONDS = 25`: HTTP/API network request timeout.

---

## 8. Vector Store Contract (`app/rag/vector_store.py`)

- **Deterministic Chunk IDs**: Eliminates random UUIDs in favor of `paper:{clean_paper_id}:chunk:{chunk_index}_{content_hash}`. Prevents duplicate chunk ingestion on retries or repeated queries.
- **Upsert Semantics**: Uses `collection.upsert()` for atomic ingestion.
- **Metadata Fields**: Stores `paper_id`, `chunk_id`, `chunk_index`, `total_chunks`, `title`, `authors`, `published`, `year`, `doi`, `paper_url`, `source`, `journal_ref`.

---

## 9. Retriever Contract (`app/rag/retriever.py`)

- **`retrieve_context(query, top_k, filters) -> List[RetrievedDocument]`**:
- Queries ChromaDB with vector embeddings and returns typed `RetrievedDocument` domain models.
- Resolves the architectural flaw from V1 where the vector store was populated but never actively queried in the research execution path.
- In `rag_node`, the vector store is populated and queried, storing `retrieved_documents` into the LangGraph state.

---

## 10. Chunking Contract (`app/rag/chunker.py`)

- Upgraded from character slicing to sentence-aware boundary chunking.
- Respects sentence terminals (`.!?\n`) with configurable sliding window overlap (`CHUNK_SIZE = 800`, `CHUNK_OVERLAP = 150`).
- Emits structured dicts with `chunk_index`, `total_chunks`, `char_start`, `char_end`, and `content`.
- Preserves backwards-compatible `chunk_text()` helper.

---

## 11. Local vs Fresh Search Integration

The engine searches both fresh external scholarly sources (`ArxivSearchProvider`) and indexed local material (`LocalCorpusProvider`). Both sources return `NormalizedPaper` instances which flow through the common deduplication and query-dependent ranking pipeline. Local documents receive no artificial preference; they must prove relevance against the active query.

---

## 12. Failure Handling and Resilience

- **Timeouts**: Provider calls timeout after 25s; provider marked as timed out in telemetry, other providers continue.
- **Network / HTTP 5xx**: HTTP errors caught, logged as structured warnings; pipeline continues.
- **Malformed Responses**: Invalid XML or JSON safely discarded; returns `[]`.
- **Empty Result Sets**: Graph transitions gracefully without crashing.
- **Provider Isolation**: A failure in arXiv does not disrupt local corpus retrieval, and vice versa.

---

## 13. Observability and Telemetry

Every search execution outputs non-sensitive structured telemetry:
```json
{
  "query": "superconducting qubit coherence fluxonium",
  "primary_query": "superconducting qubit coherence fluxonium",
  "variants_executed": 3,
  "raw_candidates_count": 28,
  "duplicates_removed": 12,
  "ranked_count": 16,
  "final_selected_count": 5,
  "provider_telemetry": {
    "arxiv": {"retrieved": 25, "status": "ok", "latency_ms": 1420},
    "local_corpus": {"retrieved": 3, "status": "ok", "latency_ms": 12}
  },
  "total_latency_ms": 1580
}
```
**Zero Secrets Policy**: No API keys, credentials, or user auth tokens are ever logged in telemetry.

---

## 14. Verification & Test Evidence

Comprehensive test suite in `tests/test_search_retrieval.py` and `tests/test_foundation.py`:
- 32 automated unit tests across query planning, normalization, deduplication, ranking, limits, vector store, and failure handling.
- **Result**: 32/32 tests pass (0 failures, 0 errors, 22.68s runtime).
- Frontend builds cleanly via Vite (`npm run build`, 1.53s).
- FastAPI `/health` endpoint verified and functional.

---

## 15. Known Limitations

- **Search Provider Breadth**: Current external provider is arXiv. Integration of additional open scholarly APIs (e.g. CrossRef, PubMed, Semantic Scholar) will follow the established `SearchProvider` contract.
- **Full Text Retrieval**: Currently indexes titles and abstracts. Full PDF extraction and parsing is intentionally deferred to Stage 3.

---

## 16. Explicit Boundary: Stage 2 vs Stage 3

| Feature / Capability | Stage 2 (Current) | Stage 3 (Next) |
|---|---|---|
| Query Planning & Search Variants | COMPLETE | Consumed |
| Provider Abstraction & arXiv Integration | COMPLETE | Consumed |
| Deterministic Deduplication | COMPLETE | Consumed |
| Query-Dependent Relevance Ranking | COMPLETE | Consumed |
| Vector Store Upsert & Retrieve Contract | COMPLETE | Consumed |
| Sentence-Level Evidence Quotes | Deferred | **STAGE 3** |
| Claim-to-Evidence Grounding | Deferred | **STAGE 3** |
| Citation Verification Pipeline | Deferred | **STAGE 3** |
| Evidence Confidence Scoring | Deferred | **STAGE 3** |
| PDF Ingestion & Semantic Slicing | Deferred | **STAGE 3** |
