"""
Deterministic Paper Deduplication Engine for Research Intelligence Assistant V2.
Implements multi-level identity resolution: DOI -> Provider ID -> Normalized URL -> Title + Author/Year fallback.
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from app.core.logging import logger
from app.models.domain import NormalizedPaper


class Deduplicator:
    """
    Deduplicates research papers using a strict, deterministic identity hierarchy.
    Merges metadata from duplicate sightings to retain the highest-fidelity record.
    """

    @staticmethod
    def normalize_doi(doi: Optional[str]) -> Optional[str]:
        """Normalizes DOI by removing URL prefixes, lowercase, and stripping whitespace."""
        if not doi:
            return None
        cleaned = doi.strip().lower()
        cleaned = re.sub(r"^https?://(dx\.)?doi\.org/", "", cleaned)
        cleaned = re.sub(r"^doi:\s*", "", cleaned)
        cleaned = cleaned.strip("/. ")
        return cleaned if cleaned else None

    @staticmethod
    def normalize_arxiv_id(paper_id: Optional[str]) -> Optional[str]:
        """Normalizes arXiv IDs by stripping version suffixes (v1, v2) and URL wrappers."""
        if not paper_id:
            return None
        cleaned = paper_id.strip().lower()
        # Extract ID from full URL if present
        match_url = re.search(r"arxiv\.org/(abs|pdf)/([^/]+?)(?:\.pdf)?(?:v\d+)?$", cleaned)
        if match_url:
            return f"arxiv:{match_url.group(2)}"
        # Extract from arxiv: prefix
        match_prefix = re.search(r"^arxiv:([0-9]+\.[0-9]+|[a-z\-]+/[0-9]+)(?:v\d+)?", cleaned)
        if match_prefix:
            return f"arxiv:{match_prefix.group(1)}"
        return None

    @staticmethod
    def normalize_url(url: Optional[str]) -> Optional[str]:
        """Normalizes URLs by removing scheme, www, tracking params, and arXiv format variance."""
        if not url:
            return None
        cleaned = url.strip().lower()

        # Handle arXiv URLs specifically
        arxiv_match = re.search(r"arxiv\.org/(abs|pdf)/([^/]+?)(?:\.pdf)?(?:v\d+)?$", cleaned)
        if arxiv_match:
            return f"arxiv.org/abs/{arxiv_match.group(2)}"

        try:
            parsed = urlparse(cleaned)
            netloc = parsed.netloc.replace("www.", "")
            path = parsed.path.rstrip("/")
            if not netloc:
                return None
            return f"{netloc}{path}"
        except Exception:
            return cleaned.rstrip("/")

    @staticmethod
    def normalize_title(title: str) -> str:
        """Removes punctuation, collapses whitespace, and converts to lowercase."""
        if not title:
            return ""
        # Remove punctuation except alphanumeric and space
        cleaned = re.sub(r"[^\w\s]", "", title.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @classmethod
    def get_author_key(cls, authors: List[str]) -> str:
        """Extracts normalized last name of the first author."""
        if not authors:
            return ""
        first = authors[0].strip().lower()
        # Take the last word as surname
        tokens = first.split()
        return tokens[-1] if tokens else ""

    def resolve_fingerprint(self, paper: NormalizedPaper) -> Tuple[str, str]:
        """
        Returns a tuple of (level, fingerprint_key).
        Levels in order of precedence: 'doi', 'provider_id', 'url', 'title_meta'.
        """
        # 1. DOI
        norm_doi = self.normalize_doi(paper.doi)
        if norm_doi:
            return ("doi", f"doi:{norm_doi}")

        # 2. arXiv / Provider ID
        norm_arxiv = self.normalize_arxiv_id(paper.paper_id or paper.id or paper.source_id)
        if norm_arxiv:
            return ("provider_id", norm_arxiv)

        # 3. Canonical URL
        norm_url = self.normalize_url(paper.paper_url)
        if norm_url:
            return ("url", f"url:{norm_url}")

        # 4. Normalized Title + Author/Year fallback
        norm_title = self.normalize_title(paper.title)
        author_key = self.get_author_key(paper.authors)
        year_key = str(paper.year) if paper.year else ""

        if len(norm_title) > 25 and (author_key or year_key):
            return ("title_meta", f"title:{norm_title}#auth:{author_key}#yr:{year_key}")
        elif len(norm_title) > 35:
            # Very long, highly specific title
            return ("title_meta", f"title:{norm_title}")

        # Fallback to unique id if too vague to risk false positive merge
        return ("unique", f"id:{paper.paper_id or paper.id or norm_title}")

    def merge_records(self, primary: NormalizedPaper, secondary: NormalizedPaper) -> NormalizedPaper:
        """
        Merges metadata from secondary into primary, retaining the highest fidelity data.
        """
        # DOI
        if not primary.doi and secondary.doi:
            primary.doi = secondary.doi

        # Year
        if not primary.year and secondary.year:
            primary.year = secondary.year

        # Abstract: keep the longer, richer abstract
        if len(secondary.abstract or "") > len(primary.abstract or ""):
            primary.abstract = secondary.abstract

        # Authors: keep more complete author list
        if len(secondary.authors or []) > len(primary.authors or []):
            primary.authors = secondary.authors

        # Journal Ref
        if not primary.journal_ref and secondary.journal_ref:
            primary.journal_ref = secondary.journal_ref

        # URL
        if not primary.paper_url and secondary.paper_url:
            primary.paper_url = secondary.paper_url

        # Citation Count
        if primary.citation_count is None and secondary.citation_count is not None:
            primary.citation_count = secondary.citation_count

        # Merge Provenance
        prov_sources = primary.provenance.get("sources", [primary.source])
        if secondary.source not in prov_sources:
            prov_sources.append(secondary.source)
        primary.provenance["sources"] = prov_sources
        primary.provenance["duplicate_merged"] = True

        return primary

    def deduplicate(self, papers: List[NormalizedPaper]) -> List[NormalizedPaper]:
        """
        Deduplicates a list of NormalizedPaper records using deterministic hierarchy.
        Preserves original order of first occurrence.
        """
        if not papers:
            return []

        seen_keys: Dict[str, NormalizedPaper] = {}
        unique_papers: List[NormalizedPaper] = []
        duplicate_count = 0

        for paper in papers:
            level, key = self.resolve_fingerprint(paper)

            if key in seen_keys:
                # Merge into existing record
                existing = seen_keys[key]
                self.merge_records(existing, paper)
                duplicate_count += 1
            else:
                seen_keys[key] = paper
                unique_papers.append(paper)

        if duplicate_count > 0:
            logger.info(f"Deduplicator merged {duplicate_count} duplicate paper records ({len(papers)} -> {len(unique_papers)})")

        return unique_papers
