"""
Stage 5 Agentic Research Loop Package.
Provides evidence sufficiency evaluation, grounded gap analysis,
targeted query reformulation, drift protection, and loop lifecycle control.
"""

from app.loop.drift_guard import QueryDriftGuard
from app.loop.evaluator import EvidenceSufficiencyEvaluator
from app.loop.gap_analyzer import ActionableGapAnalyzer
from app.loop.loop_controller import ResearchLoopController
from app.loop.query_planner import TargetedQueryPlanner

__all__ = [
    "QueryDriftGuard",
    "EvidenceSufficiencyEvaluator",
    "ActionableGapAnalyzer",
    "ResearchLoopController",
    "TargetedQueryPlanner",
]
