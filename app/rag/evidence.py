"""
Canonical Evidence Models and Registry for Research Intelligence Assistant V2 (Stage 3).
Provides run-local citation references (E001, E002), exact excerpt tracking, and session-scoped registry.

IDENTITY DISTINCTION:
- Run-Local Citation Reference: E001, E002, ... (used for prompt token efficiency, clean model citations, and run-local mapping)
- Stable Underlying Evidence Identity: paper_id + chunk_id (e.g. 'paper:{paper_id}:chunk:{idx}_{hash}' - globally stable and reproducible)
Sequential E001 numbering is explicitly run-local and scoped to an active research run, not globally deterministic across independent runs.
"""

import re
from typing import Any, Dict, List, Optional
from app.models.domain import EvidenceChunk


def generate_evidence_id(paper_id: str, chunk_index: int, sequence_num: int) -> str:
    """
    Generates a concise, run-local citation reference suitable for LLM citations and claim mapping.
    e.g. 'E001', 'E002'.
    Note: The globally stable underlying evidence identity is chunk.paper_id + chunk.chunk_id.
    """
    return f"E{sequence_num:03d}"


class EvidenceRegistry:
    """
    Session-scoped in-memory registry of validated EvidenceChunks.
    Prevents cross-run evidence contamination and serves as the single source
    of truth for claim validation and citation grounding.
    """

    def __init__(self, run_id: Optional[str] = None):
        self.run_id: str = run_id or "default_session"
        self._registry: Dict[str, EvidenceChunk] = {}
        self._paper_map: Dict[str, List[str]] = {}

    def register(self, chunk: EvidenceChunk) -> str:
        """Registers an EvidenceChunk and indexes by evidence_id and paper_id."""
        eid = chunk.evidence_id
        self._registry[eid] = chunk

        if chunk.paper_id not in self._paper_map:
            self._paper_map[chunk.paper_id] = []
        if eid not in self._paper_map[chunk.paper_id]:
            self._paper_map[chunk.paper_id].append(eid)

        return eid

    def get(self, evidence_id: str) -> Optional[EvidenceChunk]:
        """Retrieves an EvidenceChunk by ID."""
        return self._registry.get(evidence_id)

    def has(self, evidence_id: str) -> bool:
        """Returns True if evidence_id exists in this session's registry."""
        return evidence_id in self._registry

    def all_chunks(self) -> List[EvidenceChunk]:
        """Returns all registered EvidenceChunks ordered by registration."""
        return list(self._registry.values())

    def get_by_paper(self, paper_id: str) -> List[EvidenceChunk]:
        """Returns all EvidenceChunks belonging to a specific paper."""
        ids = self._paper_map.get(paper_id, [])
        return [self._registry[eid] for eid in ids if eid in self._registry]

    def count(self) -> int:
        """Returns total count of registered evidence chunks."""
        return len(self._registry)

    def to_list(self) -> List[Dict[str, Any]]:
        """Serializes registry to list of dictionaries for graph state."""
        return [chunk.model_dump() for chunk in self._registry.values()]

    @classmethod
    def from_list(cls, chunk_dicts: List[Dict[str, Any]], run_id: Optional[str] = None) -> "EvidenceRegistry":
        """Reconstructs registry from serialized state list."""
        registry = cls(run_id=run_id)
        for c_dict in chunk_dicts:
            try:
                chunk = EvidenceChunk(**c_dict)
                registry.register(chunk)
            except Exception:
                continue
        return registry
