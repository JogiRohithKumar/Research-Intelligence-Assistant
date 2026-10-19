"""
Stage 1 Foundation Smoke Tests for Research Intelligence Assistant V2.
Validates imports, configuration, domain schemas, graph compilation,
API routing, citation formatting, and query-dependent search relevance.
"""

import unittest
from pathlib import Path

from app.core.config import get_settings, Settings
from app.models.domain import (
    CandidatePaper,
    CitationItem,
    ExecutionStatus,
    FinalReport,
    GapAnalysisResult,
    UserRequest,
    VerificationResult,
)
from app.models.state import (
    PaperSummary,
    PaperSummaryList,
    QueryOptimizationResult,
    SupervisorDecision,
)
from app.services.llm_service import sanitize_raw_json
from app.agents.citation_agent import (
    generate_apa_citation,
    generate_bibtex_citation,
    generate_citations,
    generate_ieee_citation,
    generate_mla_citation,
)
from app.agents.search_agent import calculate_query_relevance
from app.graph.research_graph import research_graph
from main import app


class TestFoundationArchitecture(unittest.TestCase):

    def test_settings_load_and_defaults(self):
        """Verify centralized settings load valid defaults and resolve paths."""
        settings = get_settings()
        self.assertIsInstance(settings, Settings)
        self.assertEqual(settings.APP_NAME, "Research Intelligence Assistant V2")
        self.assertIn("gemini", settings.GEMINI_MODEL)
        self.assertTrue(settings.DATA_DIR.is_absolute())
        self.assertTrue(settings.SQLITE_DB_PATH.is_absolute())
        self.assertTrue(settings.CHROMA_PERSIST_DIRECTORY.is_absolute())

    def test_core_domain_schemas_validation(self):
        """Verify Pydantic domain models enforce strict typing and constraints."""
        # CandidatePaper
        paper = CandidatePaper(
            id="http://arxiv.org/abs/2401.00001",
            title="Attention Is All You Need",
            authors=["Vaswani et al."],
            abstract="Transformer architecture overview.",
            published="2017-06-12",
            paper_url="http://arxiv.org/abs/2401.00001",
            relevance_score=0.95
        )
        self.assertEqual(paper.title, "Attention Is All You Need")
        self.assertEqual(paper.relevance_score, 0.95)

        # UserRequest validation
        req = UserRequest(query="Quantum error correction in superconducting qubits")
        self.assertEqual(req.depth, "comprehensive")

        # VerificationResult validation
        verif = VerificationResult(
            common_findings=["Finding A", "Finding B"],
            conflicting_findings=[],
            evidence_strength="strong",
            confidence_score=0.88
        )
        self.assertEqual(len(verif.common_findings), 2)
        self.assertEqual(verif.confidence_score, 0.88)

        # GapAnalysisResult validation
        gaps = GapAnalysisResult(
            research_gaps=["Scalability gap"],
            missing_areas=["Hardware constraints"],
            future_directions=["Optical interconnects"],
            unanswered_questions=["What is the decoherence ceiling?"]
        )
        self.assertEqual(len(gaps.research_gaps), 1)

    def test_structured_llm_schemas(self):
        """Verify LLM structured output models parse and validate."""
        decision = SupervisorDecision(
            status="retry",
            reason="Query needs academic formulation",
            modified_query="synthetic biology gene circuit optimization",
            route="retry_search"
        )
        self.assertEqual(decision.status, "retry")
        self.assertEqual(decision.route, "retry_search")

        summary_list = PaperSummaryList(
            summaries=[
                PaperSummary(
                    title="Study 1",
                    summary="Summary of study 1.",
                    key_findings=["Key finding 1"]
                )
            ]
        )
        self.assertEqual(len(summary_list.summaries), 1)

    def test_json_sanitizer(self):
        """Verify JSON extraction handles markdown fences and noisy LLM output."""
        raw_markdown = """```json
{"status": "valid", "route": "continue", "reason": "Academic query verified"}
```"""
        sanitized = sanitize_raw_json(raw_markdown)
        self.assertTrue(sanitized.startswith("{"))
        self.assertTrue(sanitized.endswith("}"))

        noisy = "Here is the result:\n[{\"title\": \"Test\"}]\nHope this helps!"
        sanitized_array = sanitize_raw_json(noisy)
        self.assertTrue(sanitized_array.startswith("["))
        self.assertTrue(sanitized_array.endswith("]"))

    def test_langgraph_construction_and_nodes(self):
        """Verify LangGraph StateGraph compiles with all required Stage 1 nodes."""
        expected_nodes = {"__start__", "supervisor", "search", "rag", "summary", "citation", "intelligence", "report"}
        actual_nodes = set(research_graph.nodes.keys())
        self.assertTrue(expected_nodes.issubset(actual_nodes))

    def test_fastapi_routes_and_health(self):
        """Verify FastAPI mounts core endpoints."""
        route_paths = [route.path for route in app.routes]
        self.assertIn("/research", route_paths)
        self.assertIn("/stream", route_paths)
        self.assertIn("/health", route_paths)

    def test_citation_generation(self):
        """Verify citation generation formats APA, IEEE, MLA, and BibTeX properly."""
        sample_paper = {
            "title": "Deep Residual Learning for Image Recognition",
            "authors": ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
            "published": "2015-12-10",
            "paper_url": "https://arxiv.org/abs/1512.03385"
        }
        apa = generate_apa_citation(sample_paper)
        self.assertIn("Kaiming He", apa)
        self.assertIn("2015", apa)
        self.assertIn("Retrieved from", apa)

        ieee = generate_ieee_citation(sample_paper)
        self.assertIn("Available:", ieee)

        bibtex = generate_bibtex_citation(sample_paper)
        self.assertTrue(bibtex.startswith("@article{"))
        self.assertIn("url=", bibtex)

    def test_dynamic_search_relevance(self):
        """Verify search relevance is query-dependent and not hardcoded to fixed topics."""
        query = "cancer immunotherapy chimeric antigen receptor"
        relevant_paper = {
            "title": "Chimeric Antigen Receptor T-cell Immunotherapy in Solid Tumors",
            "abstract": "We evaluate cancer immunotherapy outcomes with engineered CAR-T cells."
        }
        irrelevant_paper = {
            "title": "Quantum Mechanics of Free Electrons in Magnetic Fields",
            "abstract": "Analysis of Landau levels and magnetic susceptibility."
        }

        rel_score = calculate_query_relevance(relevant_paper, query)
        irrel_score = calculate_query_relevance(irrelevant_paper, query)

        self.assertGreater(rel_score, 0.4)
        self.assertEqual(irrel_score, 0.0)


if __name__ == "__main__":
    unittest.main()
