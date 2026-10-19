# STAGE 3 — REAL RAG & EVIDENCE GROUNDING SPECIFICATION

**Project:** Research-Intelligence-Assistant V2  
**Date:** 2026-10-05  
**Stage:** Stage 3 — Real RAG & Evidence Grounding (Semantic Correction Pass)  
**Status:** COMPLETE & VERIFIED  

---

## 1. Stage 3 Objective

The primary objective of Stage 3 is to enforce the non-negotiable architectural invariant:
> **THE LLM MUST NOT BE ALLOWED TO MAKE A RESEARCH CLAIM UNLESS THAT CLAIM CAN BE TRACED BACK TO RETRIEVED SOURCE EVIDENCE THAT ACTUALLY SUPPORTS THE CLAIM.**

Stage 3 replaces unstructured summary generation and ungrounded citations with an auditable, evidence-first research pipeline where every factual statement maps to a verified evidence excerpt registered in a deterministic evidence registry AND is strictly evaluated by a dedicated semantic support verifier.

---

## 2. End-to-End Architecture Flow

```text
                    ┌──────────────────────────────────┐
                    │          Research Query          │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │    Scholarly Search Engine       │
                    │   (Plan -> Retrieve -> Dedup)    │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │         Candidate Papers         │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │   Vector Store Upsert & Search   │
                    │     (ChromaDB Persistent Store)  │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │        EvidenceRetriever         │
                    │ (Candidate Scoping & Dedup)      │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │         EvidenceRegistry         │
                    │ (Run-Local: E001; Stable: ChkID) │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │     EvidenceContextBuilder       │
                    │ (Demarcated Blocks & Rules)      │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │    Grounded Synthesis Agent      │
                    │ (Schema: GroundedSynthesisOutput)│
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │     ClaimEvidenceValidator       │
                    │   (ID & Session Scoping Check)   │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │      ClaimSupportVerifier        │
                    │ (Semantic Entailment & Metrics)  │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │        CitationVerifier          │
                    │ (Verify Excerpts & Quote Checks) │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │    Grounded Research Report      │
                    │ (Traceable Claims & Audit Trail) │
                    └──────────────────────────────────┘
```

---

## 3. Canonical Evidence Model & Identity Distinction

Implemented in `app/models/domain.py` and `app/rag/evidence.py`:

```python
class EvidenceSourceType(str, Enum):
    INDEXED_FULL_TEXT = "indexed_full_text"
    INDEXED_ABSTRACT = "indexed_abstract"
    PROVIDER_ABSTRACT = "provider_abstract"
    LOCAL_CORPUS = "local_corpus"

class EvidenceChunk(BaseModel):
    evidence_id: str                      # Run-local citation reference: E001, E002, ...
    paper_id: str                         # Canonical source paper ID (e.g. arxiv:2301.00001)
    chunk_id: str                         # Underlying stable vector chunk ID (e.g. paper:arxiv:...:chunk:0_hash)
    text: str                             # Exact un-paraphrased excerpt text
    title: str                            # Paper title
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    doi: Optional[str] = None
    source_url: str = ""
    provider: str = "arxiv"
    section: Optional[str] = None
    page: Optional[int] = None            # Explicitly None if PDF page unavailable (never fabricated)
    chunk_index: int = 0
    retrieval_score: float = 0.0
    evidence_source_type: EvidenceSourceType = EvidenceSourceType.INDEXED_ABSTRACT
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Clarified Evidence Identity Distinction
The architecture explicitly distinguishes between:
1. **Run-Local Citation References (`E001`, `E002`, ...)**: Compact sequential identifiers generated per research execution. These are optimized for LLM context token efficiency, human readability, and per-run citation references. They are explicitly session-scoped and NOT globally deterministic across independent runs.
2. **Stable Underlying Evidence Identity (`paper_id` + `chunk_id`)**: The deterministic identity `paper:{paper_id}:chunk:{chunk_index}_{hash}` remains globally stable, reproducible, and verifiable across ChromaDB persistence layers.

### Evidence Source Types
- `INDEXED_ABSTRACT`: Chunks retrieved from indexed paper abstracts in ChromaDB.
- `PROVIDER_ABSTRACT`: Chunks dynamically parsed from candidate paper abstracts during fallback.
- `LOCAL_CORPUS`: Chunks retrieved from local document corpus collections.
- `INDEXED_FULL_TEXT`: Not claimed in Stage 3 as full-text PDF parsing is reserved for future stages.

---

## 4. Evidence Retrieval Layer

Implemented in `app/rag/evidence_retriever.py` (`EvidenceRetriever`):
1. **Candidate Scope Enforcement**: Vector store retrieval queries are strictly filtered against candidate papers retrieved during the search phase, preventing cross-run contamination.
2. **Text Normalization & Deduplication**: Exact and whitespace-normalized excerpt hashes are tracked to eliminate duplicate evidence chunks.
3. **Similarity Filtering**: Excerpts falling below `MIN_EVIDENCE_SIMILARITY` (configured in `Settings`) are discarded.
4. **Configurable Boundaries**: Retrieval is bounded by `MAX_EVIDENCE_CHUNKS` and `MAX_CONTEXT_TOKENS`.
5. **Candidate Abstract Fallback**: If the vector store index yields 0 candidate matches, candidate abstracts are dynamically chunked and registered as direct evidence with `PROVIDER_ABSTRACT` source type (provided similarity threshold permits).

---

## 5. Evidence Provenance Chain

Every fact presented in the final synthesis is backwards-traceable:

$$\text{Final Claim} \longrightarrow \text{Claim ID } (C001) \longrightarrow \text{Evidence IDs } [E001, E002] \longrightarrow \text{Evidence Chunk} \longrightarrow \text{Chunk ID} \longrightarrow \text{Paper ID} \longrightarrow \text{Source / DOI / URL}$$

No link in this chain is fabricated or inferred.

---

## 6. Research Claim Model

Implemented in `app/models/domain.py`:

```python
class SupportVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class ClaimSupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class EvidenceSupportResult(BaseModel):
    claim_id: str
    verdict: SupportVerdict
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    explanation: str = Field(default="")

class ResearchClaim(BaseModel):
    claim_id: str                         # C001, C002, ...
    claim_text: str                       # Factual claim text
    claim_type: ClaimType = ClaimType.EMPIRICAL_FINDING
    evidence_ids: List[str] = Field(default_factory=list)
    support_status: ClaimSupportStatus = ClaimSupportStatus.UNSUPPORTED
    confidence_rationale: str = Field(default="")
    source_paper_ids: List[str] = Field(default_factory=list)
    exact_quotes: List[str] = Field(default_factory=list)
```

---

## 7. Semantic Support Verification Layer

Implemented in `app/rag/claim_support_verifier.py` (`ClaimSupportVerifier`):
A claim must **NOT** become `SUPPORTED` merely because a valid `evidence_id` exists. The verifier receives **ONLY**:
- Claim Text
- Relevant Evidence Text Excerpts
- Source Metadata (Title, Authors, Year)

### Strict Verification Rules:
1. **SUPPORTED**: The evidence directly and fully supports all factual propositions and figures in the claim (e.g. 12% improvement in outcome B compared with control group).
2. **PARTIALLY_SUPPORTED**: The evidence supports only part of the claim. Specifically triggered when:
   - Claim asserts unverified superlatives or extreme scope expansion (e.g. "outperformed all competing treatments", "superior to every").
   - Claim asserts an unverified causal mechanism (e.g. "causes higher accuracy because it reduces model bias" when evidence only showed higher accuracy).
3. **UNSUPPORTED**: The evidence is irrelevant, discusses a different topic, fails to substantiate the claim, contains missing quantitative metrics (e.g. asserts 80% error reduction when evidence has no 80%), or cites an unrelated source.
4. **INSUFFICIENT_EVIDENCE**: No evidence chunks or substantive text exist.

---

## 8. Citation Verification & Quote Integrity

Implemented in `app/rag/claim_validator.py` (`CitationVerifier`):
- **Source Verification**: Resolves every cited `evidence_id` to its source paper metadata (title, authors, year, URL, DOI).
- **Quote Integrity**: Inspects generated text for direct quotation marks (`"..."`). If a quote is asserted, the verifier checks for an exact substring match in the underlying `EvidenceChunk.text`. If the quote cannot be verified verbatim, it is flagged as a quotation fabrication failure and the claim is demoted with a caveat.
- **Audit Reporting**: Produces a `CitationVerificationResult` detailing:
  - `total_claims`
  - `supported_claims`
  - `partially_supported_claims`
  - `unsupported_claims`
  - `total_citations`
  - `valid_citations`
  - `invalid_citations`
  - `quote_integrity_failures`
  - `is_fully_grounded`

---

## 9. Unsupported Claim & Insufficient Evidence Handling

- When literature does not contain adequate evidence for a query, the system transitions to an explicit `INSUFFICIENT_EVIDENCE` status.
- Unsupported claims are presented under a distinct **Limitations & Disclosures** section rather than as grounded findings.
- When an LLM cites invalid or unsupporting evidence, the invalid references are stripped from the grounded findings.

---

## 10. Failure Modes & Mitigations

| Failure Mode | Mitigation Strategy |
| :--- | :--- |
| **Valid ID with irrelevant evidence** | `ClaimSupportVerifier` checks semantic content overlap and missing metrics; classifies as `UNSUPPORTED`. |
| **Valid ID with superlative / partial evidence** | `ClaimSupportVerifier` detects superlative scope expansion; classifies as `PARTIALLY_SUPPORTED`. |
| **Fabricated causal mechanism** | `ClaimSupportVerifier` checks causal clause coverage; classifies as `PARTIALLY_SUPPORTED`. |
| **Phantom / Hallucinated Evidence IDs** | `ClaimEvidenceValidator` checks run's `EvidenceRegistry`; purges unknown IDs and flags `UNSUPPORTED`. |
| **Fabricated verbatim quotes** | `CitationVerifier.verify_quotes()` matches quoted substrings against chunk texts; flags violations. |
| **LLM Quota / Provider failure** | Graceful fallback to deterministic heuristic synthesis preserving candidate papers and evidence chunks. |

---

## 11. Full-Text & Source Limitations (Honest Disclosure)

1. **Abstract-Level Evidence**: Search providers currently retrieve titles, abstracts, and metadata snippets. Full-text PDF layout parsing, tables, and figure coordinate mapping are **not yet implemented**.
2. **Page Numbers**: Because PDF layout analysis is not yet present, page numbers are reported as `None` and are never fabricated.
3. **Cross-Encoder Reranking**: Neural cross-encoders are deferred to avoid heavy external dependencies; dense vector similarity with candidate-scoped filtering satisfies Stage 3 retrieval accuracy.

---

## 12. Testing & Verification

Comprehensive automated test suite executed in `tests/test_rag_evidence.py` (26 tests) + full test suite (58 tests):
```bash
.\.venv-2\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```
**Results:** `Ran 58 tests in 47.274s. OK.`

### Critical Adversarial Grounding Tests:
1. `test_adversarial_valid_id_irrelevant_evidence_rejected`: Valid ID citing "Transformers trained on large text corpora" for claim "Transformers reduce medical diagnosis errors by 80%" -> marked `UNSUPPORTED`.
2. `test_adversarial_valid_id_partial_evidence_marked_partially_supported`: Valid ID citing "Treatment A improved outcome B compared with baseline" for claim "Treatment A improved outcome B and outperformed all competing treatments" -> marked `PARTIALLY_SUPPORTED`.
3. `test_strong_direct_support_marked_supported`: Valid ID citing "12% improvement in outcome B compared with control group" for claim asserting identical findings -> marked `SUPPORTED`.
4. `test_adversarial_fabricated_causal_inference_marked_partially_supported`: Valid ID citing "method A showed higher accuracy" for claim "Method A causes higher accuracy because it reduces model bias" -> marked `PARTIALLY_SUPPORTED`.
5. `test_adversarial_valid_id_unrelated_source_rejected`: Claim asserting findings about Paper A cites Evidence E002 from unrelated Paper B -> marked `UNSUPPORTED`.
6. `test_adversarial_fabricated_quote_demoted_and_flagged`: Fabricated quotation is caught by `CitationVerifier`; flagged in audit report.
7. `test_end_to_end_grounding_pipeline_with_semantic_support`: Full integration pipeline verifying supported, irrelevant, and partially-supported claims through vector retrieval, ID check, semantic support verification, citation verification, and brief generation.

---

## 13. Stage 4 Boundary Definition

Stage 3 provides the verified, grounded evidence foundation. The following analytical capabilities are strictly reserved for **Stage 4 — Research Intelligence**:
- Cross-study consensus computation (% empirical agreement across studies).
- Contradiction and conflicting findings intelligence.
- Structured research gap matrix and methodology comparison.
- Multi-step iterative research loops (reserved for Stage 5).
