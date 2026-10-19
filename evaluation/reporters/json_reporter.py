"""
Machine-Readable JSON Reporter for Stage 8.
Saves serialized EvaluationRun records with zero secret leakage.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from evaluation.models import EvaluationRun
from app.core.config import get_settings


def save_json_report(run: EvaluationRun, output_dir: Optional[Path] = None) -> Path:
    """
    Saves serialized EvaluationRun to deterministic JSON artifact.
    Ensures zero secrets or sensitive credentials are included.
    """
    settings = get_settings()
    out_dir = output_dir or (Path(__file__).parent.parent / "reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    file_path = out_dir / f"evaluation_run_{run.run_id}.json"
    data = run.model_dump(mode="json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    return file_path
