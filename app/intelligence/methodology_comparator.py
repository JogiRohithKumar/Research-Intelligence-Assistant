"""
Methodology Comparator for Research Intelligence Assistant V2 (Stage 4).
Extracts and compares paper methodologies on explicitly observed dimensions.
Never infers unstated experimental designs or superiority.
"""

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.models.domain import EvidenceChunk, PaperComparison
from app.services.llm_service import generate_structured_output


class PaperMethodologyExtraction(BaseModel):
    research_question: Optional[str] = Field(default=None, description="Exact investigated question if stated, else null")
    population: Optional[str] = Field(default=None, description="Studied subjects, domain, or model architecture if stated, else null")
    dataset: Optional[str] = Field(default=None, description="Dataset, corpus, or benchmark named in evidence, else null")
    sample_size: Optional[str] = Field(default=None, description="Sample size, parameter count, or dataset instances if stated, else null")
    intervention_or_method: Optional[str] = Field(default=None, description="Specific proposed algorithm, treatment, or architecture, else null")
    baseline_or_control: Optional[str] = Field(default=None, description="Comparison baseline or control group if stated, else null")
    outcomes: Optional[str] = Field(default=None, description="Observed outcome or primary result, else null")
    metrics: Optional[str] = Field(default=None, description="Reported evaluation metrics (e.g. accuracy, BLEU, F1), else null")
    evaluation_method: Optional[str] = Field(default=None, description="Experimental or evaluation setup if stated, else null")
    limitations: Optional[str] = Field(default=None, description="Author-stated limitations or constraints if stated, else null")
    cited_evidence_ids: List[str] = Field(default_factory=list, description="IDs of evidence chunks supporting these extractions")


class MethodologyComparator:
    """
    Extracts structured methodology dimensions across papers and constructs
    a verifiable cross-paper comparison matrix.
    """

    def extract_paper_methodology(
        self,
        paper_id: str,
        paper_title: str,
        evidence_chunks: List[EvidenceChunk]
    ) -> PaperComparison:
        """
        Extracts methodology for a single paper from its evidence chunks.
        """
        if not evidence_chunks:
            return PaperComparison(
                paper_id=paper_id,
                paper_title=paper_title,
                evidence_ids=[]
            )

        evidence_text = "\n\n".join(
            f"[{c.evidence_id}]: {c.text}" for c in evidence_chunks
        )
        evidence_ids = [c.evidence_id for c in evidence_chunks]

        prompt = f"""
Analyze the retrieved scientific evidence for paper '{paper_title}' (ID: {paper_id}).
Extract ONLY factual methodology dimensions explicitly supported by the evidence excerpts.

CRITICAL RULES:
1. If a dimension is NOT explicitly mentioned in the text, you MUST return null.
2. NEVER infer or guess sample size, dataset names, baselines, randomization, or clinical quality.
3. Every non-null field MUST be traceable to the provided evidence.
4. Set cited_evidence_ids to the list of evidence IDs ([E001], etc.) that contain the facts.

Available Evidence Excerpts:
{evidence_text}
"""
        try:
            extraction = generate_structured_output(
                prompt=prompt,
                schema=PaperMethodologyExtraction,
                system_instruction=(
                    "You are a strict academic methodology auditor. "
                    "Extract only verbatim or directly substantiated facts. Return null for absent details."
                ),
                max_retries=1
            )

            # Reconcile cited evidence IDs with actual evidence chunks
            valid_eids = [eid for eid in extraction.cited_evidence_ids if eid in evidence_ids]
            if not valid_eids:
                valid_eids = evidence_ids[:3]

            return PaperComparison(
                paper_id=paper_id,
                paper_title=paper_title,
                research_question=extraction.research_question,
                population=extraction.population,
                dataset=extraction.dataset,
                sample_size=extraction.sample_size,
                intervention_or_method=extraction.intervention_or_method,
                baseline_or_control=extraction.baseline_or_control,
                outcomes=extraction.outcomes,
                metrics=extraction.metrics,
                evaluation_method=extraction.evaluation_method,
                limitations=extraction.limitations,
                evidence_ids=valid_eids
            )
        except Exception as e:
            logger.info(f"Methodology LLM extraction fallback for paper {paper_id}: {e}")
            return self._heuristic_extraction(paper_id, paper_title, evidence_chunks)

    def _heuristic_extraction(
        self,
        paper_id: str,
        paper_title: str,
        evidence_chunks: List[EvidenceChunk]
    ) -> PaperComparison:
        """
        Deterministic keyword-based methodology extraction without LLM.
        Leaves unstated dimensions strictly as None.
        """
        combined_text = " ".join(c.text for c in evidence_chunks)
        eids = [c.evidence_id for c in evidence_chunks]

        # Dataset detection
        dataset_match = re.search(
            r"(?:dataset|benchmark|corpus|evaluated on|tested on)\s+([A-Z0-9][A-Za-z0-9_\-\s]{2,30}?)(?=[.,;\n]|\s+(?:dataset|with|and|using))",
            combined_text,
            re.IGNORECASE
        )
        dataset = dataset_match.group(0).strip() if dataset_match else None

        # Sample size / parameter detection
        sample_match = re.search(
            r"(?:sample size of|n\s*=\s*|\b\d+(?:,\d+)?\s*(?:participants|patients|subjects|examples|instances|samples|tokens|parameters))",
            combined_text,
            re.IGNORECASE
        )
        sample_size = sample_match.group(0).strip() if sample_match else None

        # Metric detection
        metric_match = re.search(
            r"(?:accuracy|f1[\s-]score|bleu|rouge|precision|recall|auc|loss|perplexity|latency|throughput)\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?%?)?",
            combined_text,
            re.IGNORECASE
        )
        metrics = metric_match.group(0).strip() if metric_match else None

        # Method / Intervention detection
        method_match = re.search(
            r"(?:we propose|we introduce|we present|method called|framework called|model called)\s+([A-Za-z0-9_\-\s]{3,40}?)(?=[.,;]|\s+(?:which|that|for))",
            combined_text,
            re.IGNORECASE
        )
        intervention = method_match.group(0).strip() if method_match else None

        # Limitations detection
        limit_match = re.search(
            r"(?:limitation|drawback|constrained by|future work|fails to|bottleneck)\s+([^.;\n]{10,80})",
            combined_text,
            re.IGNORECASE
        )
        limitations = limit_match.group(0).strip() if limit_match else None

        return PaperComparison(
            paper_id=paper_id,
            paper_title=paper_title,
            research_question=None,
            population=None,
            dataset=dataset,
            sample_size=sample_size,
            intervention_or_method=intervention,
            baseline_or_control=None,
            outcomes=metrics,
            metrics=metrics,
            evaluation_method=None,
            limitations=limitations,
            evidence_ids=eids[:3]
        )

    def compare_papers(
        self,
        candidate_papers: List[Dict[str, Any]],
        evidence_chunks: List[EvidenceChunk]
    ) -> List[PaperComparison]:
        """
        Generates PaperComparison models for all candidate papers with evidence.
        """
        # Group evidence by paper_id
        chunks_by_paper: Dict[str, List[EvidenceChunk]] = {}
        for c in evidence_chunks:
            chunks_by_paper.setdefault(c.paper_id, []).append(c)

        comparisons: List[PaperComparison] = []
        for paper in candidate_papers:
            pid = paper.get("paper_id") or paper.get("id") or ""
            title = paper.get("title", "Untitled")
            chunks = chunks_by_paper.get(pid, [])
            if not chunks:
                # If no direct vector chunks, use abstract if present
                abstract = paper.get("abstract", "")
                if abstract and pid:
                    dummy_chunk = EvidenceChunk(
                        evidence_id=f"E_{pid[:8]}",
                        paper_id=pid,
                        chunk_id=f"paper:{pid}:chunk:0_abs",
                        text=abstract,
                        title=title
                    )
                    chunks = [dummy_chunk]

            if pid and chunks:
                comp = self.extract_paper_methodology(pid, title, chunks)
                comparisons.append(comp)

        return comparisons
