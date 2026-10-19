"""
Local Corpus Search Provider for Research Intelligence Assistant V2.
Queries the local ChromaDB vector store to retrieve previously indexed papers.
"""

from typing import Any, Dict, List, Optional
from app.core.logging import logger
from app.models.domain import NormalizedPaper
from app.rag.vector_store import get_vector_collection
from app.search.base import SearchProvider


class LocalCorpusProvider(SearchProvider):
    """
    Search provider that queries locally indexed papers in ChromaDB.
    Enables hybrid retrieval across external scholarly APIs and internal corpus.
    """

    @property
    def name(self) -> str:
        return "local_corpus"

    def is_available(self) -> bool:
        try:
            coll = get_vector_collection()
            return coll is not None
        except Exception:
            return False

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[NormalizedPaper]:
        """
        Queries ChromaDB for relevant indexed chunks, collapsing chunks by paper_id.
        """
        trimmed = query.strip()
        if not trimmed:
            return []

        try:
            coll = get_vector_collection()
            count = coll.count()
            if count == 0:
                return []

            n_results = min(limit * 3, count)
            results = coll.query(
                query_texts=[trimmed],
                n_results=n_results,
                where=filters if filters else None
            )
        except Exception as e:
            logger.warning(f"LocalCorpusProvider query failed: {e}")
            return []

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        papers_by_id: Dict[str, NormalizedPaper] = {}

        for doc, meta in zip(docs, metadatas):
            if not meta:
                continue
            paper_id = meta.get("paper_id") or meta.get("paper_url") or meta.get("title", "")
            if not paper_id:
                continue

            if paper_id not in papers_by_id:
                authors_raw = meta.get("authors", "")
                authors = [a.strip() for a in authors_raw.split(",") if a.strip()] if isinstance(authors_raw, str) else []

                year_raw = meta.get("year")
                year_val = None
                if year_raw:
                    try:
                        year_val = int(year_raw)
                    except (ValueError, TypeError):
                        year_val = None

                papers_by_id[paper_id] = NormalizedPaper(
                    id=str(paper_id),
                    paper_id=str(paper_id),
                    title=str(meta.get("title", "Untitled Document")),
                    authors=authors,
                    abstract=str(doc),  # Chunk text represents context
                    published=str(meta.get("published", "")),
                    year=year_val,
                    paper_url=str(meta.get("paper_url", "")),
                    doi=meta.get("doi"),
                    source=self.name,
                    source_id=str(paper_id),
                    journal_ref=meta.get("journal_ref"),
                    paper_type="local_indexed",
                    provenance={
                        "provider": self.name,
                        "query": trimmed,
                        "indexed": True
                    }
                )

            if len(papers_by_id) >= limit:
                break

        papers = list(papers_by_id.values())
        logger.info(f"LocalCorpusProvider matched {len(papers)} papers from local Chroma collection")
        return papers
