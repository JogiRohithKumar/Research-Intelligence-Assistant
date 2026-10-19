"""
Human Review Module for Research Intelligence Assistant V2.
Provides non-blocking review interfaces suitable for web applications.
Full web-based interactive checkpoints will be implemented in Stage 5.
"""

from typing import Any, Dict


def human_review(state: Dict[str, Any], auto_approve: bool = True) -> Dict[str, Any]:
    """
    Evaluates paper summaries for human review.
    NON-BLOCKING: Replaced terminal input() to prevent web server freezes.
    Interactive interrupts and review queues are scheduled for Stage 5 (Agentic Loop).
    """
    summaries = state.get("summaries", [])
    if not summaries:
        return {"review_status": "rejected", "reason": "No summaries available for review"}

    # Default non-blocking pass-through for Stage 1 automated execution
    if auto_approve:
        return {
            "review_status": "approved",
            "reviewed_count": len(summaries),
            "mode": "automated_pass_through"
        }

    return {
        "review_status": "pending_user_input",
        "reviewed_count": len(summaries),
        "mode": "stage_5_interrupt_ready"
    }