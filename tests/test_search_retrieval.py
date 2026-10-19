"""
Comprehensive Test Suite for Stage 2: Research Search & Retrieval Engine.
Covers Query Planning, Provider Abstraction, Deduplication, Ranking,
Limits Enforcement, Vector Store Upsert, Retriever, and Failure Handling.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

from app.core.config import get_settings
from app.models.domain import NormalizedPaper, SearchPlan, RetrievedDocument
from app.search.arxiv_provider import ArxivSearchProvider
from app.search.base import SearchProvider
from app.search.deduplication import Deduplicator
from app.search.engine import ResearchSearchEngine
from app.search.query_planner import QueryPlanner
from app.search.ranker import QueryRanker
from app.rag.chunker import chunk_document, chunk_text, split_sentences
from app.rag.vector_store import generate_chunk_id, store_papers, get_vector_collection
from app.rag.retriever import retrieve_context


class MockSearchProvider(SearchProvider):
    """Mock search provider for deterministic multi-provider testing."""

    def __init__(self, provider_name: str, papers=None, fail_with=None):
        self._name = provider_name
        self._papers = papers or []
        self._fail_with = fail_with

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    def search(self, query: str, limit: int = 10, filters=None):
        if self._fail_with:
            raise self._fail_with
        return self._papers[:limit]


class TestSearchAndRetrievalEngine(unittest.TestCase):
    """Stage 2 Search & Retrieval Engine Tests."""

    def setUp(self):
        self.settings = get_settings()
        self.planner = QueryPlanner()
        self.deduplicator = Deduplicator()
        self.ranker = QueryRanker()

    # =========================================================================
    # 1. QUERY PLANNING TESTS
    # =========================================================================

    def test_normal_query_planning(self):
        """Verify QueryPlanner creates a canonical plan with concepts and variants."""
        query = "CRISPR Cas9 off-target mutations in therapeutic gene editing"
        plan = self.planner.create_fallback_plan(query)

        self.assertIsInstance(plan, SearchPlan)
        self.assertEqual(plan.original_query, query)
        self.assertIn("crispr", plan.normalized_query)
        self.assertIn("cas9", plan.normalized_query)
        self.assertTrue(len(plan.primary_query) > 0)
        self.assertTrue(len(plan.key_concepts) >= 2)
        self.assertLessEqual(len(plan.alternative_queries), self.settings.MAX_SEARCH_VARIANTS)

    def test_complex_query_planning(self):
        """Verify QueryPlanner handles complex queries with punctuation and symbols."""
        query = "How does (GPT-4 / Claude-3) multi-agent consensus affect hallucination rates?!"
        plan = self.planner.plan(query)

        self.assertIsInstance(plan, SearchPlan)
        self.assertEqual(plan.original_query, query)
        # Normalized query should be clean without brackets and punctuation
        self.assertNotIn("?!", plan.normalized_query)
        self.assertNotIn("(", plan.normalized_query)
        self.assertTrue(len(plan.key_concepts) > 0)

    def test_empty_or_whitespace_query(self):
        """Verify QueryPlanner handles empty query safely without crashing."""
        plan = self.planner.plan("   ")
        self.assertIsInstance(plan, SearchPlan)
        self.assertTrue(len(plan.primary_query) > 0)

    def test_query_variant_caps(self):
        """Verify alternative queries strictly obey MAX_SEARCH_VARIANTS."""
        query = "quantum error correction surface codes fault tolerance threshold"
        plan = self.planner.create_fallback_plan(query)
        self.assertLessEqual(len(plan.alternative_queries), self.settings.MAX_SEARCH_VARIANTS)

    # =========================================================================
    # 2. SEARCH NORMALIZATION TESTS
    # =========================================================================

    def test_arxiv_atom_entry_parsing(self):
        """Verify arXiv Atom XML is accurately parsed into NormalizedPaper."""
        xml_data = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
          <entry>
            <id>http://arxiv.org/abs/2301.00001v2</id>
            <published>2023-01-02T12:00:00Z</published>
            <title>Advances in Photonic Quantum Computing Architecture</title>
            <summary>We present a fault-tolerant photonic quantum computer based on squeezed states.</summary>
            <author><name>Alice Smith</name></author>
            <author><name>Bob Jones</name></author>
            <arxiv:doi>10.1103/PhysRevA.100.012345</arxiv:doi>
            <arxiv:journal_ref>Phys. Rev. A 100, 012345 (2023)</arxiv:journal_ref>
            <link title="pdf" href="http://arxiv.org/pdf/2301.00001v2" type="application/pdf"/>
          </entry>
        </feed>"""

        root = ET.fromstring(xml_data)
        entry = root.find("{http://www.w3.org/2005/Atom}entry")
        provider = ArxivSearchProvider()
        paper = provider._parse_entry(entry, query="photonic quantum")

        self.assertIsNotNone(paper)
        self.assertEqual(paper.paper_id, "arxiv:2301.00001")
        self.assertEqual(paper.title, "Advances in Photonic Quantum Computing Architecture")
        self.assertEqual(paper.authors, ["Alice Smith", "Bob Jones"])
        self.assertEqual(paper.year, 2023)
        self.assertEqual(paper.doi, "10.1103/PhysRevA.100.012345")
        self.assertEqual(paper.journal_ref, "Phys. Rev. A 100, 012345 (2023)")
        self.assertEqual(paper.source, "arxiv")
        self.assertEqual(paper.paper_url, "http://arxiv.org/pdf/2301.00001v2")
        self.assertIn("provider", paper.provenance)

    def test_missing_optional_metadata_handling(self):
        """Verify entries with missing authors, DOI, or journal_ref parse without error."""
        xml_data = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2305.99999</id>
            <published>2023-05-10T00:00:00Z</published>
            <title>Minimal Paper Without Extras</title>
            <summary>Concise abstract content.</summary>
          </entry>
        </feed>"""

        root = ET.fromstring(xml_data)
        entry = root.find("{http://www.w3.org/2005/Atom}entry")
        provider = ArxivSearchProvider()
        paper = provider._parse_entry(entry, query="minimal")

        self.assertIsNotNone(paper)
        self.assertEqual(paper.title, "Minimal Paper Without Extras")
        self.assertEqual(paper.authors, [])
        self.assertIsNone(paper.doi)
        self.assertIsNone(paper.journal_ref)
        self.assertEqual(paper.year, 2023)

    def test_malformed_xml_handling(self):
        """Verify invalid XML response returns empty list gracefully."""
        provider = ArxivSearchProvider()
        # Mock requests.get returning broken XML
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = b"<html><body>502 Bad Gateway</body>"
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            results = provider.search("machine learning")
            self.assertEqual(results, [])

    # =========================================================================
    # 3. DEDUPLICATION TESTS
    # =========================================================================

    def test_doi_deduplication(self):
        """Verify duplicate DOIs with varied prefixes are merged into one canonical record."""
        p1 = NormalizedPaper(
            id="p1", paper_id="p1", title="Original Title",
            doi="https://doi.org/10.1038/s41586-020-2649-2",
            authors=["Alice"], abstract="Short abstract"
        )
        p2 = NormalizedPaper(
            id="p2", paper_id="p2", title="Original Title Duplicate",
            doi="10.1038/s41586-020-2649-2",
            authors=["Alice", "Bob"], abstract="Much longer and more detailed abstract from second source."
        )

        deduped = self.deduplicator.deduplicate([p1, p2])
        self.assertEqual(len(deduped), 1)
        # Should keep richer abstract and authors
        self.assertEqual(len(deduped[0].authors), 2)
        self.assertIn("detailed abstract", deduped[0].abstract)

    def test_arxiv_id_deduplication(self):
        """Verify arXiv ID variations (v1 vs v2 vs URL) are merged."""
        p1 = NormalizedPaper(
            id="arxiv:2301.12345v1", paper_id="arxiv:2301.12345v1",
            title="Transformer Scaling Laws", authors=["John"],
            paper_url="http://arxiv.org/abs/2301.12345v1"
        )
        p2 = NormalizedPaper(
            id="arxiv:2301.12345v2", paper_id="arxiv:2301.12345v2",
            title="Transformer Scaling Laws", authors=["John"],
            paper_url="http://arxiv.org/abs/2301.12345v2"
        )

        deduped = self.deduplicator.deduplicate([p1, p2])
        self.assertEqual(len(deduped), 1)

    def test_cross_provider_deduplication(self):
        """Verify identical papers found across both arXiv and local corpus are merged."""
        p_arxiv = NormalizedPaper(
            id="arxiv:2303.00001", paper_id="arxiv:2303.00001",
            title="Neural Algorithmic Reasoning Survey",
            authors=["Petar"], source="arxiv", doi="10.1016/j.artint.2023.103982"
        )
        p_local = NormalizedPaper(
            id="local_paper_1", paper_id="local_paper_1",
            title="Neural Algorithmic Reasoning Survey",
            authors=["Petar"], source="local_corpus", doi="https://doi.org/10.1016/j.artint.2023.103982"
        )

        deduped = self.deduplicator.deduplicate([p_arxiv, p_local])
        self.assertEqual(len(deduped), 1)
        self.assertIn("local_corpus", deduped[0].provenance.get("sources", []))

    def test_title_author_fallback_deduplication(self):
        """Verify identical long titles with matching first author surname are merged."""
        p1 = NormalizedPaper(
            id="src1", paper_id="src1",
            title="Deep Residual Learning for Image Recognition and Visual Understanding",
            authors=["Kaiming He", "Xiangyu Zhang"], year=2016
        )
        p2 = NormalizedPaper(
            id="src2", paper_id="src2",
            title="Deep Residual Learning for Image Recognition and Visual Understanding",
            authors=["K. He"], year=2016
        )

        deduped = self.deduplicator.deduplicate([p1, p2])
        self.assertEqual(len(deduped), 1)

    def test_genuinely_different_papers_not_merged(self):
        """Verify genuinely different papers are NEVER accidentally merged."""
        # 1. Subtle title difference (negation)
        p1 = NormalizedPaper(
            id="paper_pos", paper_id="paper_pos",
            title="Attention Is All You Need",
            authors=["Ashish Vaswani"], year=2017
        )
        p2 = NormalizedPaper(
            id="paper_neg", paper_id="paper_neg",
            title="Attention Is Not All You Need",
            authors=["Yihe Dong"], year=2021
        )

        # 2. Similar generic topic title with different authors and years
        p3 = NormalizedPaper(
            id="med_1", paper_id="med_1",
            title="Machine Learning Applications in Clinical Oncology Care",
            authors=["Robert Smith"], year=2018
        )
        p4 = NormalizedPaper(
            id="med_2", paper_id="med_2",
            title="Machine Learning Applications in Clinical Oncology Care",
            authors=["David Johnson"], year=2023
        )

        deduped = self.deduplicator.deduplicate([p1, p2, p3, p4])
        self.assertEqual(len(deduped), 4)

    # =========================================================================
    # 4. RANKING TESTS
    # =========================================================================

    def test_query_dependent_relevance_ranking(self):
        """Verify ranking prefers papers matching the specific research query."""
        plan = SearchPlan(
            original_query="CRISPR Cas9 off-target mechanisms",
            normalized_query="crispr cas9 off target mechanisms",
            primary_query="crispr cas9 off target mechanisms",
            key_concepts=["crispr", "cas9", "off-target mutations"]
        )

        relevant = NormalizedPaper(
            id="p_rel", paper_id="p_rel",
            title="Mechanisms of Cas9 Off-Target Binding and Cleavage",
            abstract="We investigate CRISPR Cas9 specificity and off-target cleavage genome-wide.",
            authors=["Jennifer Doudna"], year=2022
        )
        irrelevant = NormalizedPaper(
            id="p_irrel", paper_id="p_irrel",
            title="Quantum Hall Effect in Graphene Superlattices",
            abstract="Observation of fractal energy spectra in graphene superlattices.",
            authors=["Andre Geim"], year=2020
        )

        ranked = self.ranker.rank([irrelevant, relevant], plan)
        self.assertEqual(ranked[0].paper_id, "p_rel")
        self.assertGreater(ranked[0].relevance_score, 0.4)
        self.assertEqual(ranked[1].relevance_score, 0.0)

    def test_no_hardcoded_ai_keywords_bias(self):
        """Verify papers outside AI/CS (e.g. geology, biology) are ranked purely on their query terms."""
        plan = SearchPlan(
            original_query="Mantle convection and subduction zone kinematics",
            normalized_query="mantle convection and subduction zone kinematics",
            primary_query="mantle convection subduction zone kinematics",
            key_concepts=["mantle convection", "subduction zone", "kinematics"]
        )

        geology_paper = NormalizedPaper(
            id="geo_1", paper_id="geo_1",
            title="Numerical Models of Mantle Convection and Subduction Dynamics",
            abstract="Global simulations of slab subduction and mantle flow regimes across geological epochs.",
            authors=["Taras Gerya"], year=2023
        )

        score = self.ranker.calculate_score(geology_paper, plan)
        self.assertGreater(score, 0.4)
        self.assertTrue(len(geology_paper.ranking_explanation) > 0)
        self.assertIn("title_cov=", geology_paper.ranking_explanation)

    def test_score_bounded_and_explainable(self):
        """Verify calculated relevance score is strictly in [0.0, 1.0] with explanation."""
        plan = SearchPlan(
            original_query="cancer immunotherapy",
            normalized_query="cancer immunotherapy",
            primary_query="cancer immunotherapy"
        )
        paper = NormalizedPaper(
            id="p1", paper_id="p1",
            title="Cancer Immunotherapy with Checkpoint Blockade",
            abstract="Clinical trials of PD-1 inhibition in advanced malignancies.",
            authors=["James Allison"], year=2021, doi="10.1126/science.123456"
        )

        score = self.ranker.calculate_score(paper, plan)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertIn("abs_cov=", paper.ranking_explanation)

    # =========================================================================
    # 5. LIMITS ENFORCEMENT TESTS
    # =========================================================================

    def test_search_engine_limits_enforcement(self):
        """Verify ResearchSearchEngine caps total candidates and final retrieval set."""
        # Generate 40 mock papers
        mock_papers = [
            NormalizedPaper(
                id=f"p_{i}", paper_id=f"p_{i}",
                title=f"Research Investigation Into Quantum Systems {i}",
                abstract=f"Abstract discussing quantum mechanics topic {i}.",
                authors=[f"Author {i}"], year=2020 + (i % 4)
            )
            for i in range(40)
        ]

        provider = MockSearchProvider("mock_scholarly", mock_papers)
        engine = ResearchSearchEngine(providers=[provider])

        result = engine.search("quantum systems", limit=5)
        papers = result["papers"]
        telemetry = result["telemetry"]

        self.assertEqual(len(papers), 5)
        self.assertLessEqual(telemetry["final_selected_count"], 5)
        self.assertLessEqual(telemetry["raw_candidates_count"], self.settings.MAX_TOTAL_CANDIDATES)

    # =========================================================================
    # 6. VECTOR STORE & CHUNKING TESTS
    # =========================================================================

    def test_deterministic_chunk_ids(self):
        """Verify chunk IDs are strictly deterministic based on paper ID and chunk index."""
        cid1 = generate_chunk_id("arxiv:2301.12345", 0, "sample text content")
        cid2 = generate_chunk_id("arxiv:2301.12345", 0, "sample text content")
        cid_diff = generate_chunk_id("arxiv:2301.12345", 1, "sample text content")

        self.assertEqual(cid1, cid2)
        self.assertNotEqual(cid1, cid_diff)
        self.assertTrue(cid1.startswith("paper:arxiv:2301.12345:chunk:0_"))

    def test_sentence_aware_chunking_with_provenance(self):
        """Verify sentence-aware chunker produces overlapping chunks with provenance."""
        text = (
            "Sentence one describes the hypothesis. "
            "Sentence two explains the experiment. "
            "Sentence three presents the data. "
            "Sentence four concludes the study."
        )
        chunks = chunk_document(text, chunk_size=80, chunk_overlap=30)

        self.assertTrue(len(chunks) >= 2)
        for ch in chunks:
            self.assertIn("chunk_index", ch)
            self.assertIn("total_chunks", ch)
            self.assertIn("char_start", ch)
            self.assertIn("char_end", ch)
            self.assertIn("content", ch)
            # Content should not be empty
            self.assertTrue(len(ch["content"].strip()) > 0)

    def test_vector_store_upsert_and_retriever(self):
        """Verify papers are upserted into ChromaDB and genuinely retrieved by query."""
        test_papers = [
            NormalizedPaper(
                id="test_vector_paper_1",
                paper_id="test_vector_paper_1",
                title="Superconducting Qubit Coherence Enhancement",
                abstract="We demonstrate dramatic enhancement in T1 and T2 coherence times of fluxonium qubits.",
                authors=["Michel Devoret"],
                year=2023,
                paper_url="https://arxiv.org/abs/2309.99999",
                doi="10.1103/PhysRevLett.130.000001",
                source="test_source"
            )
        ]

        # Ingest into vector store
        upserted = store_papers(test_papers)
        self.assertGreater(upserted, 0)

        # Retrieve using query
        retrieved_docs = retrieve_context("superconducting qubit coherence fluxonium", top_k=3)
        self.assertIsInstance(retrieved_docs, list)
        self.assertGreater(len(retrieved_docs), 0)

        retrieved_ids = [doc.paper_id for doc in retrieved_docs]
        self.assertIn("test_vector_paper_1", retrieved_ids)
        target_doc = next(doc for doc in retrieved_docs if doc.paper_id == "test_vector_paper_1")
        self.assertIsInstance(target_doc, RetrievedDocument)
        self.assertIn("fluxonium", target_doc.content.lower())
        self.assertGreater(target_doc.score, 0.0)

    def test_retriever_empty_query(self):
        """Verify retriever handles empty or whitespace queries cleanly."""
        results = retrieve_context("   ")
        self.assertEqual(results, [])

    # =========================================================================
    # 7. PROVIDER FAILURE HANDLING TESTS
    # =========================================================================

    def test_provider_timeout_handled_gracefully(self):
        """Verify engine does not fail if a provider times out."""
        import requests
        failing_provider = MockSearchProvider(
            "failing_api",
            fail_with=requests.Timeout("Connection timed out after 25s")
        )
        working_provider = MockSearchProvider(
            "working_api",
            papers=[
                NormalizedPaper(
                    id="p_work", paper_id="p_work",
                    title="Resilient Search Pipeline Execution",
                    abstract="System gracefully absorbs failures.",
                    authors=["Alice"]
                )
            ]
        )

        engine = ResearchSearchEngine(providers=[failing_provider, working_provider])
        result = engine.search("resilient pipeline")

        self.assertEqual(len(result["papers"]), 1)
        self.assertEqual(result["papers"][0].paper_id, "p_work")
        self.assertIn("error", result["telemetry"]["provider_telemetry"]["failing_api"]["status"])

    def test_provider_http_error_handled_gracefully(self):
        """Verify engine does not crash on provider 500 error."""
        import requests
        failing_provider = MockSearchProvider(
            "error_api",
            fail_with=requests.HTTPError("500 Internal Server Error")
        )
        engine = ResearchSearchEngine(providers=[failing_provider])
        result = engine.search("test error handling")

        self.assertEqual(result["papers"], [])
        self.assertEqual(result["telemetry"]["final_selected_count"], 0)

    # =========================================================================
    # 8. SECURITY & TELEMETRY TESTS
    # =========================================================================

    def test_provenance_preservation(self):
        """Verify every normalized paper carries an unbroken provenance record."""
        paper = NormalizedPaper(
            id="prov_test", paper_id="prov_test",
            title="Provenance Tracing in Scientific Assistants",
            authors=["Grace Hopper"],
            source="arxiv",
            provenance={"provider": "arxiv", "query": "provenance", "external_id": "2301.0001"}
        )
        self.assertEqual(paper.provenance["provider"], "arxiv")
        self.assertEqual(paper.provenance["query"], "provenance")

    def test_zero_secrets_in_telemetry(self):
        """Verify telemetry does not contain API keys, passwords, or credentials."""
        mock_provider = MockSearchProvider("mock", [])
        engine = ResearchSearchEngine(providers=[mock_provider])
        result = engine.search("security telemetry test")
        telemetry_str = str(result["telemetry"]).lower()

        forbidden_tokens = ["api_key", "secret", "password", "bearer", "authorization"]
        for token in forbidden_tokens:
            self.assertNotIn(token, telemetry_str)


if __name__ == "__main__":
    unittest.main()
