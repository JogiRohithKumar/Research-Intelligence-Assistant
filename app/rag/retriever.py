"""
Retriever Module for Research Intelligence Assistant V2.
Queries the vector store for relevant context chunks, mapping results to canonical RetrievedDocument records.
"""

from typing import Any, Dict, List, Optional
from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import RetrievedDocument
from app.rag.vector_store import get_vector_collection


def retrieve_context(
    query: str,
    top_k: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[RetrievedDocument]:
    """
    Retrieves the top-k most relevant document chunks for a query from ChromaDB.
    Returns typed RetrievedDocument models with source provenance.
    """
    trimmed = query.strip()
    if not trimmed:
        return []

    settings = get_settings()
    k = top_k or settings.RETRIEVAL_TOP_K

    try:
        collection = get_vector_collection()
        total_items = collection.count()
        if total_items == 0:
            logger.info("ChromaDB collection is empty; 0 documents retrieved")
            return []

        n_results = min(k, total_items)
        results = collection.query(
            query_texts=[trimmed],
            n_results=n_results,
            where=filters if filters else None,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.warning(f"Vector retrieval query failed for '{trimmed[:40]}...': {e}")
        return []

    if not results or not results.get("ids") or not results["ids"][0]:
        return []

    ids = results["ids"][0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(ids)

    retrieved: List[RetrievedDocument] = []

    for doc_id, text, meta, dist in zip(ids, docs, metas, distances):
        meta_dict = meta if isinstance(meta, dict) else {}
        paper_id = meta_dict.get("paper_id", "")
        title = meta_dict.get("title", "Untitled Document")

        # Convert distance to similarity score: distance 0 -> score 1.0
        # Euclidean or cosine distance d >= 0 -> 1.0 / (1.0 + d)
        similarity = round(1.0 / (1.0 + float(dist)), 3) if dist is not None else 0.5

        retrieved.append(
            RetrievedDocument(
                doc_id=str(doc_id),
                paper_id=str(paper_id),
                paper_title=str(title),
                content=str(text),
                chunk_index=int(meta_dict.get("chunk_index", 0)),
                score=similarity,
                metadata=meta_dict
            )
        )

    logger.info(f"Retrieved {len(retrieved)} document chunks from ChromaDB for query: '{trimmed[:40]}...'")
    return retrieved