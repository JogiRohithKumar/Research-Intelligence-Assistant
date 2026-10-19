"""
Evidence Retriever for Research Intelligence Assistant V2 (Stage 3).
Performs evidence-first retrieval against ChromaDB and candidate papers,
enforcing similarity thresholds, session isolation, and provenance tracking.
"""

import hashlib
from typing import Any, Dict, List, Optional, Set, Union
from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import EvidenceChunk, EvidenceSourceType, NormalizedPaper, RetrievedDocument
from app.rag.chunker import chunk_document
from app.rag.evidence import EvidenceRegistry, generate_evidence_id
from app.rag.retriever import retrieve_context


class EvidenceRetriever:
    """
    Retrieves and prepares verified evidence chunks from the vector store
    scoped to the active research query and candidate papers.
    """

    def __init__(self):
        self.settings = get_settings()

    def _normalize_text(self, text: str) -> str:
        """Helper to compute deterministic content hash for deduplication."""
        return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:16]

    def retrieve_evidence(
        self,
        query: str,
        papers: Optional[List[Union[Dict[str, Any], NormalizedPaper]]] = None,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
        run_id: Optional[str] = None,
        existing_registry: Optional[EvidenceRegistry] = None
    ) -> EvidenceRegistry:
        """
        Executes evidence retrieval, constructs EvidenceChunks, and returns
        a session-scoped EvidenceRegistry. Preserves existing chunks across iterations.
        """
        k = top_k or self.settings.MAX_EVIDENCE_CHUNKS
        min_score = min_similarity if min_similarity is not None else self.settings.MIN_EVIDENCE_SIMILARITY
        registry = existing_registry if existing_registry is not None else EvidenceRegistry(run_id=run_id)

        # Build candidate paper lookup to enforce session scope
        paper_lookup: Dict[str, Dict[str, Any]] = {}
        if papers:
            for p in papers:
                p_dict = p.model_dump() if hasattr(p, "model_dump") else p
                pid = str(p_dict.get("paper_id") or p_dict.get("id") or p_dict.get("paper_url", ""))
                if pid:
                    paper_lookup[pid] = p_dict

        # 1. Query vector store
        raw_docs: List[RetrievedDocument] = retrieve_context(query, top_k=k * 2)

        seen_content_hashes: Set[str] = set()
        for existing_chunk in registry.all_chunks():
            seen_content_hashes.add(self._normalize_text(existing_chunk.text))

        evidence_sequence = registry.count() + 1
        max_allowed = min(self.settings.MAX_CUMULATIVE_EVIDENCE_CHUNKS, registry.count() + k)

        for doc in raw_docs:
            if len(registry.all_chunks()) >= max_allowed:
                break

            if doc.score < min_score:
                continue

            # Session Scope Check: If candidate papers provided, ensure doc belongs to one
            matching_paper = paper_lookup.get(doc.paper_id)
            if papers and not matching_paper:
                # Try matching by title
                for cand in paper_lookup.values():
                    if cand.get("title", "").strip().lower() == doc.paper_title.strip().lower():
                        matching_paper = cand
                        break

            # If not in candidate papers and candidates exist, skip to prevent cross-run pollution
            if papers and not matching_paper:
                continue

            content_hash = self._normalize_text(doc.content)
            if content_hash in seen_content_hashes:
                continue
            seen_content_hashes.add(content_hash)

            # Metadata resolution
            meta = doc.metadata or {}
            authors_raw = meta.get("authors") or (matching_paper.get("authors") if matching_paper else [])
            if isinstance(authors_raw, str):
                authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
            elif authors_raw:
                authors = list(authors_raw)
            else:
                authors = []

            year_val = None
            raw_year = meta.get("year") or (matching_paper.get("year") if matching_paper else None)
            if raw_year:
                try:
                    year_val = int(raw_year)
                except (ValueError, TypeError):
                    year_val = None

            eid = generate_evidence_id(doc.paper_id, doc.chunk_index, evidence_sequence)
            evidence_sequence += 1

            prov_source = meta.get("source", "arxiv")
            src_type = (
                EvidenceSourceType.LOCAL_CORPUS
                if prov_source == "local_corpus"
                else EvidenceSourceType.INDEXED_ABSTRACT
            )

            chunk = EvidenceChunk(
                evidence_id=eid,
                paper_id=doc.paper_id,
                chunk_id=doc.doc_id,
                text=doc.content,
                title=doc.paper_title,
                authors=authors,
                year=year_val,
                doi=meta.get("doi") or (matching_paper.get("doi") if matching_paper else None),
                source_url=str(meta.get("paper_url") or (matching_paper.get("paper_url") if matching_paper else "") or ""),
                provider=prov_source,
                section=meta.get("section"),
                chunk_index=doc.chunk_index,
                retrieval_score=doc.score,
                evidence_source_type=src_type,
                metadata=meta
            )
            registry.register(chunk)

        # 2. Resilient fallback: If vector store had 0 matching chunks, chunk candidate abstracts directly
        # Only invoke if minimum similarity threshold allows default score (0.85)
        if registry.count() < max_allowed and papers and min_score <= 0.85:
            logger.info("Vector retrieval returned insufficient chunks; constructing evidence directly from candidate papers")
            for p in papers:
                if len(registry.all_chunks()) >= max_allowed:
                    break
                p_dict = p.model_dump() if hasattr(p, "model_dump") else p
                abstract = p_dict.get("abstract", "").strip()
                if not abstract:
                    continue

                pid = str(p_dict.get("paper_id") or p_dict.get("id") or p_dict.get("paper_url", "paper"))
                chunks = chunk_document(abstract, chunk_size=self.settings.CHUNK_SIZE, chunk_overlap=self.settings.CHUNK_OVERLAP)

                for ch in chunks:
                    if len(registry.all_chunks()) >= max_allowed:
                        break
                    ch_text = ch["content"]
                    c_hash = self._normalize_text(ch_text)
                    if c_hash in seen_content_hashes:
                        continue
                    seen_content_hashes.add(c_hash)

                    eid = generate_evidence_id(pid, ch["chunk_index"], evidence_sequence)
                    evidence_sequence += 1

                    chunk = EvidenceChunk(
                        evidence_id=eid,
                        paper_id=pid,
                        chunk_id=f"paper:{pid}:chunk:{ch['chunk_index']}",
                        text=ch_text,
                        title=p_dict.get("title", "Untitled"),
                        authors=p_dict.get("authors", []),
                        year=p_dict.get("year"),
                        doi=p_dict.get("doi"),
                        source_url=p_dict.get("paper_url", ""),
                        provider=p_dict.get("source", "arxiv"),
                        chunk_index=ch["chunk_index"],
                        retrieval_score=0.85,  # Direct candidate evidence
                        evidence_source_type=EvidenceSourceType.PROVIDER_ABSTRACT,
                        metadata={"source_direct": True}
                    )
                    registry.register(chunk)

        logger.info(f"EvidenceRetriever registered {registry.count()} verified evidence chunks for query: '{query[:40]}...'")
        return registry
