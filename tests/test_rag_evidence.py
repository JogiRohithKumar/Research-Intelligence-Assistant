"""
Comprehensive Test Suite for Stage 3: Real RAG & Evidence Grounding.
Covers Evidence Modeling, Retrieval, Context Building, Claim-to-Evidence Mapping,
Citation Verification, Quote Integrity, and Adversarial Grounding Tests.
"""

import unittest
from typing import Any, Dict, List
from pydantic import ValidationError

from app.core.config import get_settings
from app.models.domain import (
    CitationVerificationResult,
    ClaimSupportStatus,
    ClaimType,
    EvidenceChunk,
    EvidenceSourceType,
    EvidenceSupportResult,
    NormalizedPaper,
    ResearchClaim,
    SupportVerdict,
)
from app.rag.claim_support_verifier import ClaimSupportVerifier
from app.rag.claim_validator import CitationVerifier, ClaimEvidenceValidator
from app.rag.context_builder import EvidenceContextBuilder
from app.rag.evidence import EvidenceRegistry, generate_evidence_id
from app.rag.evidence_retriever import EvidenceRetriever
from app.agents.grounded_synthesis_agent import synthesize_grounded_research
from app.agents.report_agent import generate_report


class TestStage3RAGAndEvidenceGrounding(unittest.TestCase):
    """Stage 3 RAG & Evidence Grounding Automated Test Suite."""

    def setUp(self):
        self.settings = get_settings()
        self.run_id = "test_run_stage_3"
        self.registry = EvidenceRegistry(run_id=self.run_id)

        # Standard Test Evidence Chunk
        self.sample_chunk = EvidenceChunk(
            evidence_id="E001",
            paper_id="arxiv:2301.00001",
            chunk_id="paper:arxiv:2301.00001:chunk:0_abc123",
            text="We demonstrate a fault-tolerant photonic quantum processor operating at room temperature with 99.4% gate fidelity.",
            title="Photonic Quantum Computing Architecture",
            authors=["Alice Smith", "Bob Jones"],
            year=2023,
            doi="10.1103/PhysRevA.100.012345",
            source_url="http://arxiv.org/abs/2301.00001",
            provider="arxiv",
            chunk_index=0,
            retrieval_score=0.92,
            metadata={"source": "arxiv"}
        )
        self.registry.register(self.sample_chunk)

        # Secondary Test Evidence Chunk
        self.sample_chunk_2 = EvidenceChunk(
            evidence_id="E002",
            paper_id="arxiv:2302.00002",
            chunk_id="paper:arxiv:2302.00002:chunk:1_def456",
            text="Superconducting fluxonium qubits exhibit coherence times exceeding 1.2 milliseconds under optimized shielding.",
            title="High Coherence Fluxonium Circuits",
            authors=["Carol Davis"],
            year=2023,
            doi="10.1103/PhysRevLett.130.000002",
            source_url="http://arxiv.org/abs/2302.00002",
            provider="arxiv",
            chunk_index=1,
            retrieval_score=0.88,
            metadata={"source": "arxiv"}
        )
        self.registry.register(self.sample_chunk_2)

    # =========================================================================
    # 1. EVIDENCE MODEL & REGISTRY TESTS
    # =========================================================================

    def test_valid_evidence_chunk_model(self):
        """Verify EvidenceChunk instantiates correctly with all required provenance fields."""
        self.assertEqual(self.sample_chunk.evidence_id, "E001")
        self.assertEqual(self.sample_chunk.paper_id, "arxiv:2301.00001")
        self.assertEqual(self.sample_chunk.year, 2023)
        self.assertEqual(self.sample_chunk.retrieval_score, 0.92)
        self.assertIn("Alice Smith", self.sample_chunk.authors)
        self.assertEqual(self.sample_chunk.evidence_source_type, EvidenceSourceType.INDEXED_ABSTRACT)

    def test_evidence_source_type_and_identity_distinction(self):
        """Verify evidence_source_type is populated and run-local ID is distinguished from stable identity."""
        self.assertEqual(self.sample_chunk.evidence_source_type, EvidenceSourceType.INDEXED_ABSTRACT)
        self.assertEqual(self.sample_chunk.evidence_id, "E001")  # Run-local citation reference
        self.assertEqual(self.sample_chunk.chunk_id, "paper:arxiv:2301.00001:chunk:0_abc123")  # Stable chunk identity
        self.assertEqual(self.sample_chunk.paper_id, "arxiv:2301.00001")  # Stable paper identity

    def test_missing_required_fields_rejected(self):
        """Verify EvidenceChunk raises ValidationError when critical fields are missing."""
        with self.assertRaises(ValidationError):
            # Missing text and paper_id
            EvidenceChunk(evidence_id="E099", chunk_id="chk_1", title="Test")

    def test_deterministic_evidence_id_generation(self):
        """Verify evidence IDs are strictly deterministic based on sequence and paper."""
        eid_1 = generate_evidence_id("paper_1", 0, 1)
        eid_2 = generate_evidence_id("paper_1", 0, 1)
        eid_3 = generate_evidence_id("paper_1", 0, 2)

        self.assertEqual(eid_1, "E001")
        self.assertEqual(eid_2, "E001")
        self.assertEqual(eid_3, "E002")

    def test_evidence_registry_session_scoping(self):
        """Verify registry isolates chunks by run_id and provides indexed lookups."""
        reg = EvidenceRegistry(run_id="run_alpha")
        reg.register(self.sample_chunk)

        self.assertTrue(reg.has("E001"))
        self.assertFalse(reg.has("E999"))
        self.assertEqual(reg.get("E001").paper_id, "arxiv:2301.00001")
        self.assertEqual(len(reg.get_by_paper("arxiv:2301.00001")), 1)

    # =========================================================================
    # 2. EVIDENCE RETRIEVAL TESTS
    # =========================================================================

    def test_evidence_retriever_deduplication_and_limits(self):
        """Verify EvidenceRetriever deduplicates identical excerpts and obeys top_k limit."""
        retriever = EvidenceRetriever()
        mock_papers = [
            NormalizedPaper(
                id="p1", paper_id="p1",
                title="Quantum Processor Design",
                abstract="Sentence A describes processor. Sentence B describes fidelity.",
                authors=["Alice"]
            ),
            NormalizedPaper(
                id="p2", paper_id="p2",
                title="Quantum Processor Design Duplicate",
                abstract="Sentence A describes processor. Sentence B describes fidelity.",
                authors=["Alice"]
            )
        ]

        registry = retriever.retrieve_evidence(
            query="quantum processor fidelity",
            papers=mock_papers,
            top_k=5,
            run_id="dedup_test"
        )

        # Deduplication should ensure duplicate content hash appears only once
        all_texts = [c.text for c in registry.all_chunks()]
        self.assertEqual(len(all_texts), len(set(all_texts)))
        self.assertLessEqual(registry.count(), 5)

    def test_evidence_retrieval_similarity_threshold(self):
        """Verify EvidenceRetriever filters out chunks below MIN_EVIDENCE_SIMILARITY."""
        retriever = EvidenceRetriever()
        mock_paper = NormalizedPaper(
            id="p_bio", paper_id="p_bio",
            title="Photosynthetic Reaction Centers in Bacteria",
            abstract="Biological light harvesting complexes in purple bacteria.",
            authors=["Bob"]
        )

        # Query completely unrelated to photosynthesis
        registry = retriever.retrieve_evidence(
            query="fault tolerant topological quantum surface code",
            papers=[mock_paper],
            min_similarity=0.99,  # Impossibly high threshold
            run_id="thresh_test"
        )
        self.assertEqual(registry.count(), 0)

    # =========================================================================
    # 3. EVIDENCE CONTEXT BUILDER TESTS
    # =========================================================================

    def test_evidence_context_serialization_and_boundaries(self):
        """Verify context builder outputs clearly demarcated evidence blocks."""
        builder = EvidenceContextBuilder()
        context = builder.build_context(self.registry)

        self.assertIn("[E001]", context)
        self.assertIn("[E002]", context)
        self.assertIn("Paper: Photonic Quantum Computing Architecture", context)
        self.assertIn("Exact Excerpt:", context)
        self.assertIn("----------------------------------------", context)
        self.assertIn("Alice Smith", context)

    def test_evidence_context_empty_handling(self):
        """Verify context builder handles empty registry safely."""
        builder = EvidenceContextBuilder()
        empty_reg = EvidenceRegistry(run_id="empty_run")
        context = builder.build_context(empty_reg)

        self.assertEqual(context, "No verified research evidence available.")

    def test_grounding_instructions_presence(self):
        """Verify grounding rules explicitly prohibit ungrounded claims and hallucinations."""
        builder = EvidenceContextBuilder()
        rules = builder.get_grounding_instructions()

        self.assertIn("GROUNDING RULES (STRICT)", rules)
        self.assertIn("INSUFFICIENT_EVIDENCE", rules)
        self.assertIn("Do NOT fabricate", rules)

    # =========================================================================
    # 4. CLAIM MODEL & VALIDATOR TESTS
    # =========================================================================

    def test_valid_claim_validated_as_supported(self):
        """Verify a claim with valid registered evidence IDs and direct supporting text is marked SUPPORTED."""
        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C001",
            claim_text="Photonic quantum processors achieve room temperature operation with 99.4% gate fidelity.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E001"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.SUPPORTED)
        self.assertEqual(validated.source_paper_ids, ["arxiv:2301.00001"])
        self.assertTrue(len(validated.confidence_rationale) > 0)

    def test_claim_with_multiple_evidence_ids(self):
        """Verify a synthesis claim citing multiple valid evidence IDs resolves all source papers."""
        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C002",
            claim_text="Photonic processors operate at room temperature with 99.4% gate fidelity while fluxonium qubits exhibit coherence times exceeding 1.2 milliseconds.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E001", "E002"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.SUPPORTED)
        self.assertEqual(len(validated.source_paper_ids), 2)
        self.assertIn("arxiv:2301.00001", validated.source_paper_ids)
        self.assertIn("arxiv:2302.00002", validated.source_paper_ids)

    def test_unsupported_claim_without_evidence_rejected(self):
        """Verify claims with empty evidence_ids are rejected as UNSUPPORTED."""
        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C003",
            claim_text="Quantum computers have achieved exponential quantum advantage across all NP-complete problems.",
            claim_type=ClaimType.THEORETICAL,
            evidence_ids=[]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.UNSUPPORTED)
        self.assertIn("Rejected: No evidence IDs", validated.confidence_rationale)
        self.assertEqual(validated.source_paper_ids, [])

    # =========================================================================
    # 5. ADVERSARIAL GROUNDING TESTS
    # =========================================================================

    def test_adversarial_nonexistent_evidence_id_rejected(self):
        """ADVERSARIAL: Verify citing an un-retrieved, fabricated evidence ID (E999) is rejected."""
        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_BAD_1",
            claim_text="Superconducting qubits operate at 500 Kelvin without cooling.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E999"]  # Nonexistent
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.UNSUPPORTED)
        self.assertIn("Rejected: Referenced invalid/unknown", validated.confidence_rationale)
        self.assertEqual(validated.source_paper_ids, [])

    def test_adversarial_cross_run_evidence_rejected(self):
        """ADVERSARIAL: Verify evidence from another research run cannot validate claims in current run."""
        foreign_registry = EvidenceRegistry(run_id="foreign_run_123")
        foreign_chunk = EvidenceChunk(
            evidence_id="E777",
            paper_id="paper_foreign",
            chunk_id="chk_foreign",
            text="Foreign paper excerpt.",
            title="Foreign Title",
            provider="arxiv"
        )
        foreign_registry.register(foreign_chunk)

        # Active session validator uses self.registry (which does NOT contain E777)
        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_BAD_2",
            claim_text="Claim relying on foreign run evidence.",
            evidence_ids=["E777"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.UNSUPPORTED)
        self.assertIn("E777", validated.confidence_rationale)

    def test_adversarial_mixed_valid_and_invalid_evidence(self):
        """ADVERSARIAL: Claim citing one valid and one invalid ID is rejected."""
        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_BAD_3",
            claim_text="Partial truth mixed with hallucinated citation.",
            evidence_ids=["E001", "E_FAKE"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.UNSUPPORTED)
        self.assertIn("E_FAKE", validated.confidence_rationale)

    def test_adversarial_valid_id_irrelevant_evidence_rejected(self):
        """ADVERSARIAL: Evidence ID is valid, but text is irrelevant -> UNSUPPORTED."""
        trans_chunk = EvidenceChunk(
            evidence_id="E_TRANS",
            paper_id="arxiv:1706.03762",
            chunk_id="chk_trans_1",
            text="Transformers were trained on large text corpora.",
            title="Attention Is All You Need",
            provider="arxiv"
        )
        self.registry.register(trans_chunk)

        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_IRRELEVANT",
            claim_text="Transformers reduce medical diagnosis errors by 80%.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E_TRANS"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.UNSUPPORTED)

    def test_adversarial_valid_id_partial_evidence_marked_partially_supported(self):
        """ADVERSARIAL: Evidence supports part of claim, but claim asserts superlative -> PARTIALLY_SUPPORTED."""
        treat_chunk = EvidenceChunk(
            evidence_id="E_TREAT",
            paper_id="med:2023.001",
            chunk_id="chk_treat_1",
            text="Treatment A improved outcome B compared with baseline.",
            title="Clinical Study of Treatment A",
            provider="arxiv"
        )
        self.registry.register(treat_chunk)

        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_PARTIAL",
            claim_text="Treatment A improved outcome B and outperformed all competing treatments.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E_TREAT"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.PARTIALLY_SUPPORTED)

    def test_strong_direct_support_marked_supported(self):
        """Verify directly supporting evidence marks claim as SUPPORTED."""
        trial_chunk = EvidenceChunk(
            evidence_id="E_TRIAL",
            paper_id="med:2023.002",
            chunk_id="chk_trial_1",
            text="Participants receiving treatment A experienced a 12% improvement in outcome B compared with the control group.",
            title="Randomized Trial of Treatment A",
            provider="arxiv"
        )
        self.registry.register(trial_chunk)

        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_DIRECT",
            claim_text="Treatment A improved outcome B by 12% compared with the control group.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E_TRIAL"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.SUPPORTED)

    def test_adversarial_fabricated_causal_inference_marked_partially_supported(self):
        """ADVERSARIAL: Evidence observes correlation, claim invents causal mechanism -> PARTIALLY_SUPPORTED."""
        acc_chunk = EvidenceChunk(
            evidence_id="E_ACC",
            paper_id="cs:2023.003",
            chunk_id="chk_acc_1",
            text="Study participants using method A showed higher accuracy.",
            title="Empirical Evaluation of Method A",
            provider="arxiv"
        )
        self.registry.register(acc_chunk)

        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_CAUSE",
            claim_text="Method A causes higher accuracy because it reduces model bias.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E_ACC"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertIn(validated.support_status, (ClaimSupportStatus.PARTIALLY_SUPPORTED, ClaimSupportStatus.UNSUPPORTED))

    def test_adversarial_valid_id_unrelated_source_rejected(self):
        """ADVERSARIAL: Claim asserts findings about Paper A, but cites Evidence E002 from unrelated Paper B -> UNSUPPORTED."""
        validator = ClaimEvidenceValidator()
        claim = ResearchClaim(
            claim_id="C_CROSS",
            claim_text="Paper A demonstrates superconducting fluxonium qubits with coherence exceeding 10 seconds.",
            claim_type=ClaimType.EMPIRICAL_FINDING,
            evidence_ids=["E002"]
        )

        validated = validator.validate_claim(claim, self.registry)
        self.assertEqual(validated.support_status, ClaimSupportStatus.UNSUPPORTED)

    # =========================================================================
    # 6. QUOTE INTEGRITY VERIFICATION TESTS
    # =========================================================================

    def test_exact_quote_integrity_verified(self):
        """Verify verbatim quotes present in the evidence pass verification."""
        verifier = CitationVerifier()
        claim = ResearchClaim(
            claim_id="C_QUOTE_OK",
            claim_text='Authors report that "Superconducting fluxonium qubits exhibit coherence times exceeding 1.2 milliseconds".',
            evidence_ids=["E002"],
            exact_quotes=["Superconducting fluxonium qubits exhibit coherence times exceeding 1.2 milliseconds"]
        )

        failures = verifier.verify_quote_integrity(claim, self.registry)
        self.assertEqual(failures, [])

    def test_adversarial_fabricated_quote_demoted_and_flagged(self):
        """ADVERSARIAL: Quoted text fabricated by the LLM is detected and flagged."""
        verifier = CitationVerifier()
        claim = ResearchClaim(
            claim_id="C_QUOTE_FAKE",
            claim_text='Authors explicitly claim that "this processor has superseded all classical supercomputers on earth".',
            evidence_ids=["E001"],
            exact_quotes=["this processor has superseded all classical supercomputers on earth"]
        )

        result = verifier.verify_all([claim], self.registry)
        self.assertEqual(len(result.quote_integrity_failures), 1)
        self.assertEqual(result.quote_integrity_failures[0]["claim_id"], "C_QUOTE_FAKE")
        # Demoted to partially supported or flagged with caveat
        self.assertEqual(claim.support_status, ClaimSupportStatus.PARTIALLY_SUPPORTED)
        self.assertIn("unverified or paraphrased quotation", claim.confidence_rationale)

    # =========================================================================
    # 7. CITATION VERIFICATION SUITE
    # =========================================================================

    def test_citation_verifier_overall_status(self):
        """Verify CitationVerifier computes accurate aggregate audit statistics."""
        verifier = CitationVerifier()
        c1 = ResearchClaim(
            claim_id="C001",
            claim_text="Photonic quantum processors achieve room-temperature operation.",
            evidence_ids=["E001"]
        )
        c2 = ResearchClaim(
            claim_id="C002",
            claim_text="Unsupported proposition with no evidence.",
            evidence_ids=[]
        )

        audit = verifier.verify_all([c1, c2], self.registry)
        self.assertEqual(audit.total_claims, 2)
        self.assertEqual(audit.supported_claims, 1)
        self.assertEqual(audit.unsupported_claims, 1)
        self.assertEqual(audit.grounding_status, "PARTIAL")
        self.assertIn("C002", audit.unsupported_claim_ids)

    # =========================================================================
    # 8. END-TO-END INTEGRATION & TRACEABILITY TEST
    # =========================================================================

    def test_end_to_end_evidence_to_report_traceability(self):
        """
        Verify end-to-end trace:
        Claim -> Evidence ID -> Evidence Chunk -> Paper ID -> Source Citation.
        """
        query = "fault-tolerant room temperature quantum processors"
        synthesis = synthesize_grounded_research(query, self.registry)

        claims = synthesis.get("claims", [])
        self.assertGreater(len(claims), 0)

        # Inspect first claim
        top_claim = claims[0]
        self.assertTrue(len(top_claim["evidence_ids"]) > 0)
        first_eid = top_claim["evidence_ids"][0]

        # Trace backward to registry
        chunk = self.registry.get(first_eid)
        self.assertIsNotNone(chunk)
        self.assertEqual(chunk.evidence_id, first_eid)
        self.assertTrue(len(chunk.paper_id) > 0)
        self.assertTrue(len(chunk.text) > 0)

        # Render report and ensure claims are visibly cited with evidence
        report = generate_report(
            query=query,
            summaries=[{"title": chunk.title, "summary": "Test summary"}],
            citations=[{"apa": "Smith, A. (2023). Photonic Quantum Computing. arXiv."}],
            intelligence={},
            claims=claims,
            grounded_summary=synthesis.get("grounded_summary"),
            citation_verification=synthesis.get("verification"),
            evidence_registry=self.registry.to_list()
        )

        self.assertIn("## Verified Grounded Claims", report)
        self.assertIn(f"Citing: [{first_eid}]", report)
        self.assertIn("## Evidence Grounding & Verification", report)
        self.assertIn("Grounding Status:", report)
        # Ensure NO fake confidence scores appear in report
        self.assertNotIn("Confidence Score:", report)

    def test_end_to_end_grounding_pipeline_with_semantic_support(self):
        """
        Integration test verifying complete Stage 3 grounding pipeline:
        query -> search -> retrieve evidence -> claim generation -> ID validation
        -> SEMANTIC SUPPORT VERIFICATION -> citation verification -> grounded claims.
        Proves:
        1. directly supported claim is marked SUPPORTED
        2. irrelevant-evidence claim is marked UNSUPPORTED
        3. partially-supported claim is marked PARTIALLY_SUPPORTED
        """
        # 1. Setup candidate papers
        paper_quantum = NormalizedPaper(
            id="arxiv:2301.00001",
            paper_id="arxiv:2301.00001",
            title="Photonic Quantum Computing Architecture",
            abstract="We demonstrate a fault-tolerant photonic quantum processor operating at room temperature with 99.4% gate fidelity.",
            authors=["Alice Smith", "Bob Jones"]
        )
        paper_medical = NormalizedPaper(
            id="med:2023.001",
            paper_id="med:2023.001",
            title="Clinical Evaluation of Treatment A",
            abstract="Treatment A improved outcome B compared with baseline across 200 patients.",
            authors=["Dr. Adams"]
        )

        # 2. Retrieve evidence
        retriever = EvidenceRetriever()
        registry = retriever.retrieve_evidence(
            query="quantum processor fidelity and clinical outcomes",
            papers=[paper_quantum, paper_medical],
            run_id="e2e_semantic_test"
        )
        self.assertGreater(registry.count(), 0)

        quantum_eid = registry.get_by_paper("arxiv:2301.00001")[0].evidence_id
        medical_eid = registry.get_by_paper("med:2023.001")[0].evidence_id

        # 3. Create three test claims representing the required categories:
        # Category 1: Directly supported claim
        claim_supported = ResearchClaim(
            claim_id="C_E2E_1",
            claim_text="Photonic quantum processors achieve room temperature operation with 99.4% gate fidelity.",
            evidence_ids=[quantum_eid]
        )

        # Category 2: Irrelevant-evidence claim (cites quantum evidence for medical diagnosis claim)
        claim_irrelevant = ResearchClaim(
            claim_id="C_E2E_2",
            claim_text="Quantum processors reduce hospital patient readmission rates by 95%.",
            evidence_ids=[quantum_eid]
        )

        # Category 3: Partially supported claim (cites medical evidence but inflates with superlative)
        claim_partial = ResearchClaim(
            claim_id="C_E2E_3",
            claim_text="Treatment A improved outcome B and outperformed all competing treatments.",
            evidence_ids=[medical_eid]
        )

        # 4. Run through ClaimEvidenceValidator (executes ID check + semantic support verification)
        validator = ClaimEvidenceValidator()
        v_sup = validator.validate_claim(claim_supported, registry)
        v_irr = validator.validate_claim(claim_irrelevant, registry)
        v_part = validator.validate_claim(claim_partial, registry)

        self.assertEqual(v_sup.support_status, ClaimSupportStatus.SUPPORTED)
        self.assertEqual(v_irr.support_status, ClaimSupportStatus.UNSUPPORTED)
        self.assertEqual(v_part.support_status, ClaimSupportStatus.PARTIALLY_SUPPORTED)

        # 5. Run through CitationVerifier
        verifier = CitationVerifier()
        audit = verifier.verify_all([v_sup, v_irr, v_part], registry)

        self.assertEqual(audit.total_claims, 3)
        self.assertEqual(audit.supported_claims, 1)  # v_sup (fully supported)
        self.assertEqual(audit.partially_supported_claims, 1)  # v_part (partially supported)
        self.assertEqual(audit.unsupported_claims, 1)  # v_irr (unsupported)
        self.assertIn("C_E2E_2", audit.unsupported_claim_ids)
        self.assertEqual(audit.grounding_status, "PARTIAL")

        # 6. Render final report and verify formatting
        report = generate_report(
            query="quantum and clinical outcomes",
            summaries=[],
            citations=[],
            intelligence={},
            claims=[v_sup.model_dump(), v_irr.model_dump(), v_part.model_dump()],
            grounded_summary="Synthesis of quantum architecture and clinical treatment outcomes.",
            citation_verification=audit.model_dump(),
            evidence_registry=registry.to_list()
        )

        self.assertIn("## Verified Grounded Claims", report)
        self.assertIn(f"[{v_sup.claim_id}]", report)
        self.assertIn(f"(Citing: [{quantum_eid}])", report)
        self.assertIn("*(Partially Supported)*", report)
        self.assertIn("*(Unsupported)*", report)
        self.assertIn("Verified Grounded Claims:** 1 / 3", report)


if __name__ == "__main__":
    unittest.main()
