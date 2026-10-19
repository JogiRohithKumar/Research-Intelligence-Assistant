"""
RAG and Evidence Grounding Package for Research Intelligence Assistant V2 (Stage 3).
"""

from app.rag.chunker import chunk_document, chunk_text
from app.rag.vector_store import store_papers, get_vector_collection, generate_chunk_id
from app.rag.retriever import retrieve_context
from app.rag.evidence import EvidenceRegistry, generate_evidence_id
from app.rag.evidence_retriever import EvidenceRetriever
from app.rag.context_builder import EvidenceContextBuilder
from app.rag.claim_validator import ClaimEvidenceValidator, CitationVerifier
from app.rag.claim_support_verifier import ClaimSupportVerifier

__all__ = [
    "chunk_document",
    "chunk_text",
    "store_papers",
    "get_vector_collection",
    "generate_chunk_id",
    "retrieve_context",
    "EvidenceRegistry",
    "generate_evidence_id",
    "EvidenceRetriever",
    "EvidenceContextBuilder",
    "ClaimEvidenceValidator",
    "CitationVerifier",
    "ClaimSupportVerifier",
]
