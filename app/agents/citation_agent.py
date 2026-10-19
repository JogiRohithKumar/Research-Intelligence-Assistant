"""
Citation Agent for Research Intelligence Assistant V2.
Generates deterministic APA, IEEE, MLA, and BibTeX citations for research papers.
"""

from typing import Any, Dict, List
from app.models.domain import CitationItem


def generate_apa_citation(paper: Dict[str, Any]) -> str:
    authors = paper.get("authors") or ["Unknown Author"]
    authors_str = ", ".join(authors)
    year = str(paper.get("published", "n.d."))[:4]
    title = paper.get("title", "Untitled")
    url = paper.get("paper_url", "")
    retrieved = f" Retrieved from {url}" if url else ""
    return f"{authors_str} ({year}). {title}.{retrieved}".strip()


def generate_ieee_citation(paper: Dict[str, Any]) -> str:
    authors = paper.get("authors") or ["Unknown Author"]
    authors_str = ", ".join(authors)
    year = str(paper.get("published", "n.d."))[:4]
    title = paper.get("title", "Untitled")
    url = paper.get("paper_url", "")
    online = f" [Online]. Available: {url}" if url else ""
    return f'{authors_str}, "{title}," arXiv, {year}.{online}'.strip()


def generate_mla_citation(paper: Dict[str, Any]) -> str:
    authors = paper.get("authors") or ["Unknown Author"]
    authors_str = ", ".join(authors)
    year = str(paper.get("published", "n.d."))[:4]
    title = paper.get("title", "Untitled")
    url = paper.get("paper_url", "")
    url_str = f" {url}." if url else ""
    return f'{authors_str}. "{title}." arXiv, {year}.{url_str}'.strip()


def generate_bibtex_citation(paper: Dict[str, Any]) -> str:
    authors = paper.get("authors") or ["Author"]
    first_author = authors[0].split()[-1].lower() if authors[0] else "author"
    year = str(paper.get("published", "2026"))[:4]
    key = f"{first_author}{year}"
    title = paper.get("title", "Untitled")
    url = paper.get("paper_url", "")
    authors_bib = " and ".join(authors)

    return f"""@article{{{key},
  title={{ {title} }},
  author={{ {authors_bib} }},
  year={{ {year} }},
  url={{ {url} }}
}}""".strip()


def generate_citations(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generates citations across 4 major academic citation formats."""
    citations: List[Dict[str, Any]] = []

    for paper in papers:
        item = CitationItem(
            title=paper.get("title", "Untitled"),
            apa=generate_apa_citation(paper),
            ieee=generate_ieee_citation(paper),
            mla=generate_mla_citation(paper),
            bibtex=generate_bibtex_citation(paper),
        )
        citations.append(item.model_dump())

    return citations