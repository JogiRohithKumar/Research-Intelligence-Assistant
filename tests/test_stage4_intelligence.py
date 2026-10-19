"""
Automated Test Suite for Stage 4 — Research Intelligence.
Verifies cross-paper agreement, genuine vs false contradictions,
methodology comparison, research gap detection, evidence strength classification,
adversarial unsupported intelligence rejection, and strict provenance enforcement.
"""

import unittest
from unittest.mock import MagicMock, patch

from app.intelligence.consensus_synthesizer import ConsensusSynthesizer
from app.intelligence.contradiction_detector import ContradictionDetector
from app.intelligence.cross_paper_analyzer import CrossPaperAnalyzer
from app.intelligence.evidence_strength_evaluator import EvidenceStrengthEvaluator
from app.intelligence.methodology_comparator import MethodologyComparator
from app.intelligence.provenance_guard import ProvenanceGuard
from app.intelligence.research_gap_detector import ResearchGapDetector
from app.intelligence.engine import ResearchIntelligenceEngine
from app.graph.research_graph import research_graph
from app.models.domain import (
    ClaimSupportStatus,
    ContradictionFinding,
    ContradictionType,
    EvidenceChunk,
    EvidenceSourceType,
    EvidenceStrength,
    EvidenceStrengthRating,
    FindingType,
    PaperComparison,
    ResearchClaim,
    ResearchFinding,
    ResearchGapCategory,
    ResearchGapFinding,
)


class TestStage4ResearchIntelligence(unittest.TestCase):
    """
    Test suite for Stage 4 Research Intelligence components.
    """

    def setUp(self):
        # Base fixtures: Two papers on sparse attention
        self.chunk_p1 = EvidenceChunk(
            evidence_id="E001",
            paper_id="arxiv:2301.00001",
            chunk_id="paper:arxiv:2301.00001:chunk:0_abc",
            text="FlashAttention achieves a 2.4x speedup and reduces memory footprint on the LongRangeArena benchmark.",
            title="Fast and Memory-Efficient Exact Attention",
            authors=["Dao, T.", "Fu, D."],
            year=2022,
            doi="10.48550/arXiv.2205.14135",
            source_url="https://arxiv.org/abs/2205.14135",
            evidence_source_type=EvidenceSourceType.INDEXED_ABSTRACT,
        )

        self.chunk_p2 = EvidenceChunk(
            evidence_id="E002",
            paper_id="arxiv:2302.00002",
            chunk_id="paper:arxiv:2302.00002:chunk:0_def",
            text="TritonAttention reduces memory consumption by 2.2x and improves inference speed across sequence lengths up to 8k.",
            title="Accelerating Transformer Inference",
            authors=["Smith, J.", "Triton, P."],
            year=2023,
            doi="10.48550/arXiv.2302.00002",
            source_url="https://arxiv.org/abs/2302.00002",
            evidence_source_type=EvidenceSourceType.INDEXED_ABSTRACT,
        )

        self.chunk_p3_contradictory = EvidenceChunk(
            evidence_id="E003",
            paper_id="arxiv:2303.00003",
            chunk_id="paper:arxiv:2303.00003:chunk:0_ghi",
            text="FlashAttention fails to reduce memory consumption and degrades throughput on sequence lengths under 512.",
            title="Evaluating Attention Mechanisms on Short Sequences",
            authors=["Johnson, M."],
            year=2023,
            doi="10.48550/arXiv.2303.00003",
            source_url="https://arxiv.org/abs/2303.00003",
            evidence_source_type=EvidenceSourceType.INDEXED_ABSTRACT,
        )

        self.claim_p1 = ResearchClaim(
            claim_id="C001",
            claim_text="FlashAttention achieves speedup and reduces memory footprint on LongRangeArena.",
            evidence_ids=["E001"],
            source_paper_ids=["arxiv:2301.00001"],
            support_status=ClaimSupportStatus.SUPPORTED,
        )

        self.claim_p2 = ResearchClaim(
            claim_id="C002",
            claim_text="TritonAttention reduces memory consumption and improves inference speed.",
            evidence_ids=["E002"],
            source_paper_ids=["arxiv:2302.00002"],
            support_status=ClaimSupportStatus.SUPPORTED,
        )

        self.candidate_papers = [
            {
                "paper_id": "arxiv:2301.00001",
                "title": "Fast and Memory-Efficient Exact Attention",
                "abstract": self.chunk_p1.text,
            },
            {
                "paper_id": "arxiv:2302.00002",
                "title": "Accelerating Transformer Inference",
                "abstract": self.chunk_p2.text,
            }
        ]

    # -------------------------------------------------------------
    # 1. Cross-Paper Agreement
    # -------------------------------------------------------------
    def test_cross_paper_agreement(self):
        """
        Two papers with compatible directional findings should yield an AGREEMENT finding.
        """
        analyzer = CrossPaperAnalyzer(evidence_chunks=[self.chunk_p1, self.chunk_p2])
        comparisons = [
            PaperComparison(
                paper_id="arxiv:2301.00001",
                intervention_or_method="FlashAttention",
                metrics="2.4x speedup",
                evidence_ids=["E001"]
            ),
            PaperComparison(
                paper_id="arxiv:2302.00002",
                intervention_or_method="TritonAttention",
                metrics="2.2x speedup",
                evidence_ids=["E002"]
            )
        ]

        findings = analyzer.analyze_cross_paper(
            claims=[self.claim_p1, self.claim_p2],
            comparisons=comparisons,
            contradictions=[],
            query="attention memory reduction"
        )

        self.assertTrue(len(findings) > 0)
        agreement_findings = [f for f in findings if f.finding_type == FindingType.AGREEMENT]
        self.assertTrue(len(agreement_findings) > 0)
        first_agreement = agreement_findings[0]
        self.assertIn("arxiv:2301.00001", first_agreement.paper_ids)
        self.assertIn("arxiv:2302.00002", first_agreement.paper_ids)
        self.assertTrue(any(eid in ["E001", "E002"] for eid in first_agreement.evidence_ids))

    # -------------------------------------------------------------
    # 2. False Contradiction (Different Datasets / Settings)
    # -------------------------------------------------------------
    def test_false_contradiction_rejected(self):
        """
        Two papers with different datasets but different numbers must NOT be classified as genuine contradiction.
        """
        detector = ContradictionDetector(evidence_chunks=[self.chunk_p1, self.chunk_p2])

        # Claim A: 91% on Dataset X
        claim_a = ResearchClaim(
            claim_id="C010",
            claim_text="Model achieves 91% accuracy on Dataset X.",
            evidence_ids=["E001"],
            source_paper_ids=["arxiv:2301.00001"],
            support_status=ClaimSupportStatus.SUPPORTED
        )
        # Claim B: 87% on Dataset Y
        claim_b = ResearchClaim(
            claim_id="C011",
            claim_text="Model achieves 87% accuracy on Dataset Y.",
            evidence_ids=["E002"],
            source_paper_ids=["arxiv:2302.00002"],
            support_status=ClaimSupportStatus.SUPPORTED
        )

        comparisons = [
            PaperComparison(
                paper_id="arxiv:2301.00001",
                dataset="Dataset X",
                metrics="91% accuracy",
                evidence_ids=["E001"]
            ),
            PaperComparison(
                paper_id="arxiv:2302.00002",
                dataset="Dataset Y",
                metrics="87% accuracy",
                evidence_ids=["E002"]
            )
        ]

        contradictions = detector.detect_contradictions(
            claims=[claim_a, claim_b],
            comparisons=comparisons
        )

        # Must not be flagged as a genuine contradiction
        genuine_conflicts = [c for c in contradictions if c.is_genuine_contradiction]
        self.assertEqual(len(genuine_conflicts), 0, "Different datasets should not trigger genuine contradiction")

    # -------------------------------------------------------------
    # 3. Genuine Contradiction
    # -------------------------------------------------------------
    def test_genuine_contradiction_detected(self):
        """
        Two papers making incompatible claims about the same method/condition
        must be classified as a genuine CONTRADICTION.
        """
        detector = ContradictionDetector(evidence_chunks=[self.chunk_p1, self.chunk_p3_contradictory])

        claim_positive = ResearchClaim(
            claim_id="C020",
            claim_text="FlashAttention improves memory efficiency and throughput.",
            evidence_ids=["E001"],
            source_paper_ids=["arxiv:2301.00001"],
            support_status=ClaimSupportStatus.SUPPORTED
        )

        claim_negative = ResearchClaim(
            claim_id="C021",
            claim_text="FlashAttention fails to reduce memory consumption and degrades throughput.",
            evidence_ids=["E003"],
            source_paper_ids=["arxiv:2303.00003"],
            support_status=ClaimSupportStatus.SUPPORTED
        )

        comparisons = [
            PaperComparison(
                paper_id="arxiv:2301.00001",
                intervention_or_method="FlashAttention",
                outcomes="improves efficiency",
                evidence_ids=["E001"]
            ),
            PaperComparison(
                paper_id="arxiv:2303.00003",
                intervention_or_method="FlashAttention",
                outcomes="degrades throughput",
                evidence_ids=["E003"]
            )
        ]

        contradictions = detector.detect_contradictions(
            claims=[claim_positive, claim_negative],
            comparisons=comparisons
        )

        self.assertTrue(len(contradictions) > 0)
        genuine = [c for c in contradictions if c.is_genuine_contradiction]
        self.assertTrue(len(genuine) > 0, "Direct result conflict under same method must be genuine contradiction")
        self.assertEqual(genuine[0].contradiction_type, ContradictionType.DIRECT_RESULT_CONFLICT)

    # -------------------------------------------------------------
    # 4. Methodology Difference
    # -------------------------------------------------------------
    def test_methodology_difference_not_direct_conflict(self):
        """
        Different outcomes produced under different methodologies must be classified
        as METHODOLOGY_DEPENDENT rather than direct contradiction.
        """
        detector = ContradictionDetector(evidence_chunks=[self.chunk_p1, self.chunk_p2])

        claim_m1 = ResearchClaim(
            claim_id="C030",
            claim_text="Method A improves latency using custom kernel optimization.",
            evidence_ids=["E001"],
            source_paper_ids=["arxiv:2301.00001"],
            support_status=ClaimSupportStatus.SUPPORTED
        )
        claim_m2 = ResearchClaim(
            claim_id="C031",
            claim_text="Method B fails to improve latency under standard PyTorch loops.",
            evidence_ids=["E002"],
            source_paper_ids=["arxiv:2302.00002"],
            support_status=ClaimSupportStatus.SUPPORTED
        )

        comparisons = [
            PaperComparison(
                paper_id="arxiv:2301.00001",
                intervention_or_method="custom kernel",
                evidence_ids=["E001"]
            ),
            PaperComparison(
                paper_id="arxiv:2302.00002",
                intervention_or_method="standard PyTorch",
                evidence_ids=["E002"]
            )
        ]

        contradictions = detector.detect_contradictions(
            claims=[claim_m1, claim_m2],
            comparisons=comparisons
        )

        self.assertTrue(len(contradictions) > 0)
        self.assertFalse(contradictions[0].is_genuine_contradiction)
        self.assertEqual(contradictions[0].contradiction_type, ContradictionType.METHODOLOGY_DEPENDENT)

    # -------------------------------------------------------------
    # 5. Research Gap Detection
    # -------------------------------------------------------------
    def test_research_gap_detection(self):
        """
        When evidence is concentrated on a single dataset or author limitation,
        a structured research gap must be detected with the 'Within the retrieved literature' prefix.
        """
        detector = ResearchGapDetector(evidence_chunks=[self.chunk_p1, self.chunk_p2])
        comparisons = [
            PaperComparison(
                paper_id="arxiv:2301.00001",
                dataset="LongRangeArena",
                limitations="Constrained by SRAM buffer size",
                evidence_ids=["E001"]
            ),
            PaperComparison(
                paper_id="arxiv:2302.00002",
                dataset="LongRangeArena",
                limitations="Requires CUDA compute capability 8.0+",
                evidence_ids=["E002"]
            )
        ]

        gaps = detector.detect_gaps(
            comparisons=comparisons,
            claims=[self.claim_p1, self.claim_p2],
            query="transformer attention limits"
        )

        self.assertTrue(len(gaps) > 0)
        first_gap = gaps[0]
        self.assertTrue(first_gap.description.startswith("Within the retrieved literature"))
        self.assertTrue(len(first_gap.affected_papers) > 0)
        self.assertTrue(len(first_gap.supporting_evidence_ids) > 0)

    # -------------------------------------------------------------
    # 6. Insufficient Evidence Handling
    # -------------------------------------------------------------
    def test_insufficient_evidence_no_fake_consensus(self):
        """
        When zero or minimal evidence exists, the evaluator must classify strength as INSUFFICIENT
        and consensus must explicitly state evidence is insufficient without fake consensus.
        """
        evaluator = EvidenceStrengthEvaluator()
        strength = evaluator.evaluate_strength(
            claims=[],
            evidence_chunks=[],
            contradictions=[],
            findings=[]
        )

        self.assertEqual(strength.rating, EvidenceStrengthRating.INSUFFICIENT)
        self.assertIn("insufficient", strength.rationale.lower())

        synthesizer = ConsensusSynthesizer()
        consensus = synthesizer.synthesize_consensus(
            query="obscure non-existent topic",
            findings=[],
            contradictions=[],
            comparisons=[],
            evidence_strength=strength,
            gaps=[],
            evidence_chunks=[]
        )

        self.assertEqual(consensus.consensus_status, "INSUFFICIENT_EVIDENCE")
        self.assertIn("insufficient to establish a reliable consensus", consensus.synthesis_statement)

    # -------------------------------------------------------------
    # 7. Evidence Strength Ratings
    # -------------------------------------------------------------
    def test_evidence_strength_classification(self):
        """
        Tests:
        - Conflicting evidence -> MIXED
        - Single study -> LIMITED
        - Multi-study consistent -> MODERATE / STRONG
        """
        evaluator = EvidenceStrengthEvaluator()

        # Mixed conflict test
        mock_conflict = ContradictionFinding(
            contradiction_id="CT001",
            topic="Memory efficiency",
            paper_a_id="arxiv:2301.00001",
            paper_b_id="arxiv:2303.00003",
            claim_a="Improves memory",
            claim_b="Degrades memory",
            evidence_ids=["E001", "E003"],
            contradiction_type=ContradictionType.DIRECT_RESULT_CONFLICT,
            is_genuine_contradiction=True
        )
        mixed_strength = evaluator.evaluate_strength(
            claims=[self.claim_p1],
            evidence_chunks=[self.chunk_p1, self.chunk_p3_contradictory],
            contradictions=[mock_conflict],
            findings=[]
        )
        self.assertEqual(mixed_strength.rating, EvidenceStrengthRating.MIXED)

        # Single study test
        single_strength = evaluator.evaluate_strength(
            claims=[self.claim_p1],
            evidence_chunks=[self.chunk_p1],
            contradictions=[],
            findings=[]
        )
        self.assertEqual(single_strength.rating, EvidenceStrengthRating.LIMITED)

        # Multi-study consistent (4+ papers)
        chunks_multi = [
            self.chunk_p1,
            self.chunk_p2,
            EvidenceChunk(evidence_id="E004", paper_id="arxiv:p4", chunk_id="chk4", text="t4", title="P4"),
            EvidenceChunk(evidence_id="E005", paper_id="arxiv:p5", chunk_id="chk5", text="t5", title="P5"),
        ]
        strong_strength = evaluator.evaluate_strength(
            claims=[self.claim_p1, self.claim_p2],
            evidence_chunks=chunks_multi,
            contradictions=[],
            findings=[]
        )
        self.assertEqual(strong_strength.rating, EvidenceStrengthRating.STRONG)

    # -------------------------------------------------------------
    # 8. Adversarial Unsupported Intelligence Rejection
    # -------------------------------------------------------------
    def test_adversarial_unsupported_consensus_rejected(self):
        """
        If an LLM or finding claims 'All studies agree' while contradictions exist,
        the system must reject or qualify the conclusion.
        """
        analyzer = CrossPaperAnalyzer(evidence_chunks=[self.chunk_p1, self.chunk_p3_contradictory])

        contradiction = ContradictionFinding(
            contradiction_id="CT001",
            topic="throughput",
            paper_a_id="arxiv:2301.00001",
            paper_b_id="arxiv:2303.00003",
            claim_a="Improves throughput",
            claim_b="Degrades throughput",
            evidence_ids=["E001", "E003"],
            contradiction_type=ContradictionType.DIRECT_RESULT_CONFLICT,
            is_genuine_contradiction=True
        )

        adversarial_finding = ResearchFinding(
            finding_id="F999",
            finding_text="All studies agree that FlashAttention provides uniform improvements.",
            finding_type=FindingType.AGREEMENT,
            claim_ids=["C001"],
            evidence_ids=["E001"],
            paper_ids=["arxiv:2301.00001", "arxiv:2303.00003"]
        )

        qualified = analyzer._enforce_adversarial_qualification(
            findings=[adversarial_finding],
            contradictions=[contradiction]
        )

        self.assertEqual(len(qualified), 1)
        res = qualified[0]
        self.assertEqual(res.finding_type, FindingType.QUALIFIED_CONCLUSION)
        self.assertNotIn("All studies agree", res.finding_text)
        self.assertIn("Qualified", res.explanation)

    # -------------------------------------------------------------
    # 9. Provenance Verification Guard
    # -------------------------------------------------------------
    def test_provenance_verification_purges_hallucinated_ids(self):
        """
        Findings that reference non-existent evidence IDs (e.g. E999) must be
        purged by ProvenanceGuard before promoting to final report.
        """
        guard = ProvenanceGuard(
            evidence_chunks=[self.chunk_p1, self.chunk_p2],
            claims=[self.claim_p1, self.claim_p2],
            candidate_papers=self.candidate_papers
        )

        valid_finding = ResearchFinding(
            finding_id="F001",
            finding_text="Valid finding with verified provenance.",
            claim_ids=["C001"],
            evidence_ids=["E001"],
            paper_ids=["arxiv:2301.00001"]
        )

        hallucinated_finding = ResearchFinding(
            finding_id="F002",
            finding_text="Hallucinated finding citing phantom evidence.",
            claim_ids=["C001"],
            evidence_ids=["E999"],  # Non-existent
            paper_ids=["arxiv:2301.00001"]
        )

        audit = guard.audit_and_filter_findings(
            findings=[valid_finding, hallucinated_finding],
            comparisons=[],
            contradictions=[],
            gaps=[]
        )

        promoted = audit["findings"]
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0].finding_id, "F001")
        self.assertEqual(audit["audit_summary"]["rejected_findings_count"], 1)

    # -------------------------------------------------------------
    # 10. End-to-End Research Intelligence Engine Analysis
    # -------------------------------------------------------------
    def test_end_to_end_research_intelligence_engine(self):
        """
        Executes ResearchIntelligenceEngine.analyze() and validates
        that all Stage 4 models are populated with intact provenance and zero fake metrics.
        """
        engine = ResearchIntelligenceEngine()
        result = engine.analyze(
            query="efficient attention mechanisms",
            papers=self.candidate_papers,
            evidence_chunks=[self.chunk_p1, self.chunk_p2],
            claims=[self.claim_p1, self.claim_p2]
        )

        self.assertIn("findings", result)
        self.assertIn("comparisons", result)
        self.assertIn("contradictions", result)
        self.assertIn("gaps", result)
        self.assertIn("consensus", result)
        self.assertIn("evidence_strength", result)
        self.assertIn("provenance_audit", result)

        self.assertTrue(result["provenance_audit"]["chain_intact"])
        # Verify no fake confidence score
        self.assertEqual(result["verification"]["confidence_score"], 0.0)
        self.assertIn(result["evidence_strength"]["rating"], ["STRONG", "MODERATE", "LIMITED", "MIXED", "INSUFFICIENT"])

    # -------------------------------------------------------------
    # 11. Mocked LLM Structured Cross-Paper Analysis
    # -------------------------------------------------------------
    @patch("app.intelligence.cross_paper_analyzer.generate_structured_output")
    def test_llm_cross_paper_analysis_mocked(self, mock_llm):
        """
        Verifies that when LLM returns structured cross-paper analysis,
        it parses and constructs verified ResearchFinding objects.
        """
        from app.intelligence.cross_paper_analyzer import LLMCrossPaperAnalysisReport, LLMFindingItem
        mock_llm.return_value = LLMCrossPaperAnalysisReport(
            findings=[
                LLMFindingItem(
                    finding_text="Both studies demonstrate significant reductions in memory footprint.",
                    finding_type=FindingType.AGREEMENT,
                    claim_ids=["C001", "C002"],
                    cited_evidence_ids=["E001", "E002"],
                    paper_ids=["arxiv:2301.00001", "arxiv:2302.00002"],
                    explanation="Multi-paper empirical concordance."
                )
            ]
        )

        analyzer = CrossPaperAnalyzer(evidence_chunks=[self.chunk_p1, self.chunk_p2])
        findings = analyzer.analyze_cross_paper(
            claims=[self.claim_p1, self.claim_p2],
            comparisons=[],
            contradictions=[],
            query="memory reduction"
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].finding_type, FindingType.AGREEMENT)
        self.assertIn("Both studies demonstrate", findings[0].finding_text)
        self.assertEqual(findings[0].evidence_ids, ["E001", "E002"])

    # -------------------------------------------------------------
    # 12. Mocked LLM Contradiction Detection
    # -------------------------------------------------------------
    @patch("app.intelligence.contradiction_detector.generate_structured_output")
    def test_llm_contradiction_detection_mocked(self, mock_llm):
        """
        Verifies that when LLM returns structured contradiction analysis,
        genuine vs false contradictions are accurately handled.
        """
        from app.intelligence.contradiction_detector import LLMContradictionReport, LLMContradictionItem
        mock_llm.return_value = LLMContradictionReport(
            contradictions=[
                LLMContradictionItem(
                    topic="throughput scaling",
                    paper_a_id="arxiv:2301.00001",
                    paper_b_id="arxiv:2303.00003",
                    claim_a="FlashAttention improves throughput",
                    claim_b="FlashAttention degrades throughput",
                    cited_evidence_ids=["E001", "E003"],
                    contradiction_type=ContradictionType.DIRECT_RESULT_CONFLICT,
                    is_genuine_contradiction=True,
                    possible_explanations=["Sequence length regime differences"]
                )
            ]
        )

        detector = ContradictionDetector(evidence_chunks=[self.chunk_p1, self.chunk_p3_contradictory])
        contradictions = detector.detect_contradictions(
            claims=[self.claim_p1],
            comparisons=[]
        )

        self.assertEqual(len(contradictions), 1)
        self.assertTrue(contradictions[0].is_genuine_contradiction)
        self.assertEqual(contradictions[0].contradiction_type, ContradictionType.DIRECT_RESULT_CONFLICT)
        self.assertIn("Sequence length", contradictions[0].possible_explanations[0])

    # -------------------------------------------------------------
    # 13. Mocked LLM Research Gap Detection
    # -------------------------------------------------------------
    @patch("app.intelligence.research_gap_detector.generate_structured_output")
    def test_llm_research_gap_detection_mocked(self, mock_llm):
        """
        Verifies that when LLM returns structured research gaps,
        category and mandatory prefix are enforced.
        """
        from app.intelligence.research_gap_detector import LLMResearchGapReport, LLMResearchGapItem
        mock_llm.return_value = LLMResearchGapReport(
            gaps=[
                LLMResearchGapItem(
                    category=ResearchGapCategory.POPULATION_GAP,
                    description="long-context models above 64k tokens remain unexamined in retrieved benchmarks.",
                    affected_papers=["arxiv:2301.00001"],
                    cited_evidence_ids=["E001"],
                    reasoning="Studies evaluated up to 8k context length."
                )
            ]
        )

        detector = ResearchGapDetector(evidence_chunks=[self.chunk_p1])
        gaps = detector.detect_gaps(
            comparisons=[],
            claims=[self.claim_p1],
            query="transformer context window"
        )

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].category, ResearchGapCategory.POPULATION_GAP)
        self.assertTrue(gaps[0].description.startswith("Within the retrieved literature"))

    # -------------------------------------------------------------
    # 14. Mocked LLM Methodology Extraction
    # -------------------------------------------------------------
    @patch("app.intelligence.methodology_comparator.generate_structured_output")
    def test_llm_methodology_extraction_mocked(self, mock_llm):
        """
        Verifies that methodology extraction retains verbatim fields and preserves nulls.
        """
        from app.intelligence.methodology_comparator import PaperMethodologyExtraction
        mock_llm.return_value = PaperMethodologyExtraction(
            research_question="Can attention computation be exact and IO-aware?",
            dataset="LongRangeArena",
            sample_size=None,  # Not stated
            intervention_or_method="FlashAttention",
            baseline_or_control="Standard PyTorch Self-Attention",
            metrics="2.4x speedup",
            limitations="Requires CUDA-capable hardware",
            cited_evidence_ids=["E001"]
        )

        comparator = MethodologyComparator()
        comp = comparator.extract_paper_methodology(
            paper_id="arxiv:2301.00001",
            paper_title="Fast and Memory-Efficient Exact Attention",
            evidence_chunks=[self.chunk_p1]
        )

        self.assertEqual(comp.dataset, "LongRangeArena")
        self.assertIsNone(comp.sample_size, "Unstated sample size must remain None")
        self.assertEqual(comp.intervention_or_method, "FlashAttention")
        self.assertEqual(comp.metrics, "2.4x speedup")

    # -------------------------------------------------------------
    # 15. Mocked LLM Consensus Synthesis
    # -------------------------------------------------------------
    @patch("app.intelligence.consensus_synthesizer.generate_structured_output")
    def test_llm_consensus_synthesis_mocked(self, mock_llm):
        """
        Verifies that consensus synthesis constructs grounded multi-paper collective findings.
        """
        from app.intelligence.consensus_synthesizer import LLMConsensusOutput
        mock_llm.return_value = LLMConsensusOutput(
            synthesis_statement="Retrieved studies consistently demonstrate that IO-aware attention reduces memory footprint.",
            divergent_points=["Performance gains vary based on GPU SRAM capacity."],
            cited_evidence_ids=["E001", "E002"]
        )

        synthesizer = ConsensusSynthesizer()
        strength = EvidenceStrength(
            rating=EvidenceStrengthRating.STRONG,
            rationale="Multi-study convergence",
            supporting_paper_count=2,
            evidence_chunks_count=2
        )

        consensus = synthesizer.synthesize_consensus(
            query="IO-aware attention",
            findings=[],
            contradictions=[],
            comparisons=[],
            evidence_strength=strength,
            gaps=[],
            evidence_chunks=[self.chunk_p1, self.chunk_p2]
        )

        self.assertEqual(consensus.consensus_status, "ESTABLISHED")
        self.assertIn("IO-aware attention reduces memory", consensus.synthesis_statement)
        self.assertEqual(len(consensus.divergent_points), 1)

    # -------------------------------------------------------------
    # 16. Full LangGraph Stage 4 Pipeline Execution
    # -------------------------------------------------------------
    def test_full_langgraph_stage4_pipeline_execution(self):
        """
        Executes the compiled research_graph with an initial research state
        and verifies that Stage 4 intelligence artifacts and final report are populated.
        """
        import time
        thread_id = f"test_stage4_graph_{int(time.time())}"

        initial_state = {
            "query": "superconducting qubit coherence fluxonium",
            "thread_id": thread_id,
            "retry_count": 0,
            "execution_status": "in_progress",
            "supervisor": None,
            "search_plan": None,
            "papers": [],
            "retrieved_documents": [],
            "evidence_registry": [],
            "claims": [],
            "grounded_summary": "",
            "citation_verification": None,
            "grounding_status": "UNGROUNDED",
            "summaries": [],
            "citations": [],
            "verification": None,
            "gaps": None,
            "intelligence": None,
            "cross_paper_findings": [],
            "study_comparisons": [],
            "contradiction_findings": [],
            "evidence_strength": None,
            "research_gaps": [],
            "consensus_synthesis": None,
            "report": "",
            "final_report": None,
            "agent_logs": [],
            "errors": []
        }

        config = {"configurable": {"thread_id": thread_id}}
        final_state = research_graph.invoke(initial_state, config=config)

        self.assertEqual(final_state["execution_status"], "completed")
        self.assertIn("report", final_state)
        self.assertTrue(len(final_state["report"]) > 0)
        self.assertIn("intelligence", final_state)

        # Check Stage 4 state fields are populated
        self.assertIsNotNone(final_state.get("intelligence"))
        self.assertIn("cross_paper_findings", final_state)
        self.assertIn("study_comparisons", final_state)
        self.assertIn("contradiction_findings", final_state)
        self.assertIn("evidence_strength", final_state)
        self.assertIn("research_gaps", final_state)
        self.assertIn("consensus_synthesis", final_state)

        # Verify that final report contains Stage 4 sections
        report_text = final_state["report"]
        self.assertIn("# Academic Research Intelligence Brief", report_text)
        self.assertIn("## Executive Summary & Collective Consensus", report_text)
        self.assertIn("## Evidence Strength Assessment", report_text)


if __name__ == "__main__":
    unittest.main()
