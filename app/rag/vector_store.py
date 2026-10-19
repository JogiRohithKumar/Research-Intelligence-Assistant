"""
Vector Store Management for Research Intelligence Assistant V2.
Provides deterministic upsert and enriched metadata storage with ChromaDB.
"""

import hashlib
import re
from typing import Any, Dict, List, Optional, Union
import chromadb

from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import NormalizedPaper
from app.rag.chunker import chunk_document

_client = None
_collection = None


def get_vector_collection():
    """Initializes and returns the ChromaDB persistent collection."""
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        settings.ensure_directories()
        _client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIRECTORY))
        _collection = _client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
    return _collection


def generate_chunk_id(paper_id: str, chunk_index: int, content: Optional[str] = None) -> str:
    """
    Generates a deterministic ID for a chunk to prevent duplicate ingestion:
    format: 'paper:{clean_paper_id}:chunk:{chunk_index}'
    """
    # Sanitize paper_id to alphanumeric and clean delimiters
    clean_id = re.sub(r"[^\w\-\.:]", "_", paper_id or "paper").strip("_")
    if not clean_id:
        clean_id = "unknown_paper"

    if content:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
        return f"paper:{clean_id}:chunk:{chunk_index}_{content_hash}"

    return f"paper:{clean_id}:chunk:{chunk_index}"


def store_papers(papers: List[Union[Dict[str, Any], NormalizedPaper]]) -> int:
    """
    Stores paper chunks into ChromaDB with deterministic IDs and enriched metadata.
    Uses upsert to prevent duplication across runs or retries.
    """
    if not papers:
        return 0

    target_collection = get_vector_collection()
    total_stored = 0

    for item in papers:
        # Support both Pydantic models and dictionaries
        if isinstance(item, NormalizedPaper):
            paper_dict = item.model_dump()
        elif isinstance(item, dict):
            paper_dict = item
        else:
            continue

        abstract = paper_dict.get("abstract", "").strip()
        if not abstract:
            continue

        paper_id = (
            paper_dict.get("paper_id")
            or paper_dict.get("id")
            or paper_dict.get("paper_url")
            or paper_dict.get("title", "paper")
        )
        title = paper_dict.get("title", "")
        published = paper_dict.get("published", "")
        year = str(paper_dict.get("year", "")) if paper_dict.get("year") is not None else ""
        doi = str(paper_dict.get("doi", "") or "")
        url = paper_dict.get("paper_url", "")
        source = paper_dict.get("source", "arxiv")
        journal_ref = str(paper_dict.get("journal_ref", "") or "")

        authors_raw = paper_dict.get("authors", [])
        if isinstance(authors_raw, list):
            authors_str = ", ".join(authors_raw)
        else:
            authors_str = str(authors_raw)

        # Generate structured sentence-aware chunks
        chunks = chunk_document(abstract)
        if not chunks:
            continue

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for ch in chunks:
            idx = ch["chunk_index"]
            text_content = ch["content"]
            cid = generate_chunk_id(str(paper_id), idx, text_content)

            ids.append(cid)
            documents.append(text_content)
            metadatas.append({
                "paper_id": str(paper_id),
                "chunk_id": cid,
                "chunk_index": idx,
                "total_chunks": ch["total_chunks"],
                "title": str(title),
                "authors": str(authors_str),
                "published": str(published),
                "year": year,
                "doi": doi,
                "paper_url": str(url),
                "source": str(source),
                "journal_ref": journal_ref,
            })

        if ids:
            target_collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            total_stored += len(ids)

    logger.info(f"Upserted {total_stored} chunks across {len(papers)} papers into ChromaDB")
    return total_stored