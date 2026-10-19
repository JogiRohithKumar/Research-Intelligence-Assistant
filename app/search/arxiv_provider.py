"""
ArXiv Search Provider for Research Intelligence Assistant V2.
Communicates with arXiv API, parses Atom XML, and normalizes into NormalizedPaper records.
"""

import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
import requests

from app.core.config import get_settings
from app.core.logging import logger
from app.models.domain import NormalizedPaper
from app.search.base import SearchProvider


class ArxivSearchProvider(SearchProvider):
    """
    Scholarly search provider backed by the official arXiv API.
    Handles XML parsing, metadata extraction, rate limits, and timeouts.
    """

    BASE_URL = "http://export.arxiv.org/api/query"
    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def __init__(self):
        self.settings = get_settings()

    @property
    def name(self) -> str:
        return "arxiv"

    def is_available(self) -> bool:
        return True

    def _extract_arxiv_id(self, raw_id: str) -> str:
        """Extracts the canonical arXiv identifier from an ID URL."""
        match = re.search(r"arxiv\.org/abs/([^/v]+)(v\d+)?", raw_id)
        if match:
            return match.group(1).strip()
        # Fallback for older format (e.g. math/0501234)
        match_old = re.search(r"arxiv\.org/abs/([a-zA-Z\-]+/\d+)", raw_id)
        if match_old:
            return match_old.group(1).strip()
        return raw_id.strip()

    def _clean_text(self, text: Optional[str]) -> str:
        """Normalizes whitespace and removes line breaks."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _parse_entry(self, entry: ET.Element, query: str) -> Optional[NormalizedPaper]:
        """Parses a single Atom entry element into a NormalizedPaper model."""
        try:
            # Title
            title_node = entry.find("atom:title", self.NAMESPACES)
            title = self._clean_text(title_node.text if title_node is not None else "")
            if not title or title.lower() == "untitled":
                return None

            # Summary / Abstract
            summary_node = entry.find("atom:summary", self.NAMESPACES)
            abstract = self._clean_text(summary_node.text if summary_node is not None else "")

            # Entry ID & canonical arXiv ID
            id_node = entry.find("atom:id", self.NAMESPACES)
            raw_id = id_node.text.strip() if id_node is not None and id_node.text else ""
            clean_id = self._extract_arxiv_id(raw_id)
            paper_id = f"arxiv:{clean_id}" if clean_id else raw_id

            # Authors
            authors: List[str] = []
            for author_elem in entry.findall("atom:author", self.NAMESPACES):
                name_elem = author_elem.find("atom:name", self.NAMESPACES)
                if name_elem is not None and name_elem.text:
                    cleaned_name = self._clean_text(name_elem.text)
                    if cleaned_name:
                        authors.append(cleaned_name)

            # Published Date & Year
            pub_node = entry.find("atom:published", self.NAMESPACES)
            published = pub_node.text.strip() if pub_node is not None and pub_node.text else ""
            year: Optional[int] = None
            if published and len(published) >= 4:
                try:
                    year = int(published[:4])
                except ValueError:
                    year = None

            # PDF / Paper URL
            paper_url = raw_id
            for link in entry.findall("atom:link", self.NAMESPACES):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    paper_url = link.attrib.get("href", paper_url)
                    break
                elif link.attrib.get("rel") == "alternate":
                    paper_url = link.attrib.get("href", paper_url)

            # DOI
            doi_node = entry.find("arxiv:doi", self.NAMESPACES)
            doi = doi_node.text.strip() if doi_node is not None and doi_node.text else None

            # Journal Ref
            journal_node = entry.find("arxiv:journal_ref", self.NAMESPACES)
            journal_ref = self._clean_text(journal_node.text if journal_node is not None else "") or None

            return NormalizedPaper(
                id=paper_id,
                paper_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract,
                published=published,
                year=year,
                paper_url=paper_url,
                doi=doi,
                source=self.name,
                source_id=clean_id,
                journal_ref=journal_ref,
                paper_type="preprint",
                provenance={
                    "provider": self.name,
                    "query": query,
                    "raw_id": raw_id,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to parse arXiv entry: {e}")
            return None

    def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[NormalizedPaper]:
        """
        Executes query against arXiv API and returns parsed NormalizedPaper records.
        """
        trimmed = query.strip()
        if not trimmed:
            return []

        # Build clean search query for arXiv
        # Clean tokens to avoid malformed arXiv query syntax
        safe_tokens = [
            re.sub(r"[^\w\-]", "", t) for t in trimmed.split()
            if len(re.sub(r"[^\w\-]", "", t)) > 1
        ][:6]

        if not safe_tokens:
            search_query = f"all:{urllib.parse.quote(trimmed)}"
        else:
            # Search both title and abstract for top tokens
            sub_clauses = [f"(ti:{t}+OR+abs:{t})" for t in safe_tokens[:4]]
            search_query = "+AND+".join(sub_clauses)

        max_results = min(limit, self.settings.MAX_RESULTS_PER_PROVIDER)
        url = f"{self.BASE_URL}?search_query={search_query}&start=0&max_results={max_results}"

        headers = {
            "User-Agent": f"ResearchIntelligenceAssistant/{self.settings.APP_VERSION} (Academic Rebuild; mailto:research@example.com)"
        }

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=self.settings.SEARCH_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except requests.Timeout:
            logger.warning(f"ArXiv provider timed out after {self.settings.SEARCH_TIMEOUT_SECONDS}s for query '{trimmed}'")
            return []
        except requests.RequestException as re_err:
            logger.warning(f"ArXiv provider HTTP/network error for query '{trimmed}': {re_err}")
            return []
        except ET.ParseError as pe_err:
            logger.warning(f"ArXiv provider returned invalid XML for query '{trimmed}': {pe_err}")
            return []
        except Exception as err:
            logger.error(f"Unexpected error in ArXiv search for query '{trimmed}': {err}")
            return []

        papers: List[NormalizedPaper] = []
        for entry in root.findall("atom:entry", self.NAMESPACES):
            paper = self._parse_entry(entry, query=trimmed)
            if paper is not None:
                papers.append(paper)

        logger.info(f"ArXivProvider retrieved {len(papers)} papers for query: '{trimmed}'")
        return papers
