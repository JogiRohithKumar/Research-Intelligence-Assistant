"""
Research Intelligence Package for Research Intelligence Assistant V2 (Stage 4).
Contains production-grade cross-paper analysis, agreement & contradiction detection,
methodology comparison, evidence strength assessment, and research gap detection.
"""

from app.intelligence.provenance_guard import ProvenanceGuard
from app.intelligence.methodology_comparator import MethodologyComparator
from app.intelligence.contradiction_detector import ContradictionDetector
from app.intelligence.cross_paper_analyzer import CrossPaperAnalyzer
from app.intelligence.evidence_strength_evaluator import EvidenceStrengthEvaluator
from app.intelligence.research_gap_detector import ResearchGapDetector
from app.intelligence.consensus_synthesizer import ConsensusSynthesizer
from app.intelligence.engine import ResearchIntelligenceEngine

__all__ = [
    "ProvenanceGuard",
    "MethodologyComparator",
    "ContradictionDetector",
    "CrossPaperAnalyzer",
    "EvidenceStrengthEvaluator",
    "ResearchGapDetector",
    "ConsensusSynthesizer",
    "ResearchIntelligenceEngine",
]
