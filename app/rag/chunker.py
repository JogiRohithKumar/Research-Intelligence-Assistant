"""
Sentence-Aware Text Chunker for Research Intelligence Assistant V2.
Prepares documents for deterministic vector indexing and RAG retrieval
with sliding window overlap and provenance tracking.
"""

import re
from typing import Any, Dict, List, Optional
from app.core.config import get_settings


def split_sentences(text: str) -> List[str]:
    """Splits text into sentences based on punctuation and whitespace boundaries."""
    if not text:
        return []
    # Split on sentence terminals followed by space or newline
    sentence_end_pattern = r"(?<=[.!?])\s+"
    raw_sentences = re.split(sentence_end_pattern, text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences if sentences else [text.strip()]


def chunk_document(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Creates sentence-aware overlapping chunks preserving character offsets and index metadata.
    Does not silently truncate text.
    """
    if not text or not text.strip():
        return []

    settings = get_settings()
    c_size = chunk_size or settings.CHUNK_SIZE
    c_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    # Ensure valid overlap
    if c_overlap >= c_size:
        c_overlap = c_size // 4

    sentences = split_sentences(text)
    chunks_raw: List[Dict[str, Any]] = []

    current_chunk: List[str] = []
    current_length = 0

    for sent in sentences:
        sent_len = len(sent)
        if current_length + sent_len > c_size and current_chunk:
            # Finalize current chunk
            chunk_str = " ".join(current_chunk).strip()
            chunks_raw.append({"content": chunk_str})

            # Calculate overlap from trailing sentences
            overlap_sentences: List[str] = []
            overlap_len = 0
            for s in reversed(current_chunk):
                if overlap_len + len(s) <= c_overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s)
                else:
                    break

            current_chunk = overlap_sentences + [sent]
            current_length = sum(len(s) for s in current_chunk) + len(current_chunk)
        else:
            current_chunk.append(sent)
            current_length += sent_len + 1

    if current_chunk:
        chunk_str = " ".join(current_chunk).strip()
        chunks_raw.append({"content": chunk_str})

    # Add index and provenance metadata
    total_chunks = len(chunks_raw)
    base_meta = metadata or {}
    structured_chunks: List[Dict[str, Any]] = []

    char_cursor = 0
    for idx, c in enumerate(chunks_raw):
        content = c["content"]
        # Find rough start in original text
        start_idx = text.find(content[:30], char_cursor) if len(content) >= 30 else char_cursor
        if start_idx == -1:
            start_idx = char_cursor
        end_idx = start_idx + len(content)
        char_cursor = max(char_cursor, start_idx + 1)

        structured_chunks.append({
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "content": content,
            "char_start": start_idx,
            "char_end": end_idx,
            **base_meta
        })

    return structured_chunks


def chunk_text(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> List[str]:
    """
    Backwards-compatible API returning list of string chunks.
    Uses sentence-aware chunking with overlap.
    """
    chunks = chunk_document(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [c["content"] for c in chunks]