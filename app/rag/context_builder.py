"""
Evidence Context Builder for Research Intelligence Assistant V2 (Stage 3).
Converts retrieved EvidenceChunks into an explicit, LLM-safe context with strict source boundaries.
"""

from typing import List, Optional, Union
from app.core.config import get_settings
from app.models.domain import EvidenceChunk
from app.rag.evidence import EvidenceRegistry


class EvidenceContextBuilder:
    """
    Constructs isolated evidence blocks for LLM synthesis prompts,
    enforcing token bounds and provenance preservation.
    """

    def __init__(self):
        self.settings = get_settings()

    def build_context(
        self,
        evidence: Union[EvidenceRegistry, List[EvidenceChunk]],
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Builds a clearly demarcated evidence context string.
        """
        chunks: List[EvidenceChunk] = (
            evidence.all_chunks() if isinstance(evidence, EvidenceRegistry) else evidence
        )

        if not chunks:
            return "No verified research evidence available."

        token_cap = max_tokens or self.settings.MAX_CONTEXT_TOKENS
        # Approximate 1 token ~= 4 characters
        char_cap = token_cap * 4

        blocks: List[str] = []
        current_char_count = 0

        for chunk in chunks:
            authors_str = ", ".join(chunk.authors) if chunk.authors else "Unknown Authors"
            year_str = f" ({chunk.year})" if chunk.year else ""
            doi_str = f" | DOI: {chunk.doi}" if chunk.doi else ""
            url_str = f" | URL: {chunk.source_url}" if chunk.source_url else ""

            block = (
                f"[{chunk.evidence_id}]\n"
                f"Paper: {chunk.title}\n"
                f"Authors: {authors_str}{year_str}\n"
                f"Provider: {chunk.provider}{doi_str}{url_str}\n"
                f"Exact Excerpt:\n"
                f'"{chunk.text.strip()}"\n'
                f"----------------------------------------"
            )

            if current_char_count + len(block) > char_cap and blocks:
                break

            blocks.append(block)
            current_char_count += len(block)

        return "\n\n".join(blocks)

    def get_grounding_instructions(self) -> str:
        """
        Returns strict system constraints for LLM evidence grounding.
        """
        return (
            "GROUNDING RULES (STRICT):\n"
            "1. You must state factual research claims ONLY if directly supported by the [EVIDENCE E...] blocks above.\n"
            "2. Every claim MUST explicitly reference the supporting evidence ID(s), e.g. ['E001', 'E002'].\n"
            "3. Do NOT invent evidence IDs or citations that are not listed in the supplied context.\n"
            "4. Do NOT fabricate quotations. If you quote a text, it MUST match the exact excerpt.\n"
            "5. If the provided evidence is insufficient to address an aspect of the query, explicitly declare INSUFFICIENT_EVIDENCE.\n"
            "6. Keep inference distinct from evidence."
        )
