"""
Stage 2 Retrieval Metrics.
Computes Recall@K, Precision@K, Hit@K, MRR, duplicate rate, and irrelevant retrieval rate.
"""

from typing import List, Set


def _normalize(text: str) -> str:
    return "".join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()


def calculate_hit_at_k(retrieved: List[str], ground_truth: List[str], k: int = 5) -> float:
    """Computes Hit@K (1.0 if at least one ground-truth item is in top-K, 0.0 otherwise)."""
    if not ground_truth:
        return 1.0
    top_k = [_normalize(item) for item in retrieved[:k]]
    gt_set = {_normalize(item) for item in ground_truth}
    for item in top_k:
        if any(gt in item or item in gt for gt in gt_set):
            return 1.0
    return 0.0


def calculate_precision_at_k(retrieved: List[str], ground_truth: List[str], k: int = 5) -> float:
    """Computes Precision@K: proportion of top-K items that are relevant."""
    if not retrieved or k <= 0:
        return 0.0
    top_k = [_normalize(item) for item in retrieved[:k]]
    gt_set = {_normalize(item) for item in ground_truth}
    relevant_hits = 0
    for item in top_k:
        if any(gt in item or item in gt for gt in gt_set):
            relevant_hits += 1
    return round(relevant_hits / min(k, len(retrieved)), 4)


def calculate_recall_at_k(retrieved: List[str], ground_truth: List[str], k: int = 5) -> float:
    """Computes Recall@K: proportion of ground-truth relevant items retrieved in top-K."""
    if not ground_truth:
        return 1.0
    top_k = [_normalize(item) for item in retrieved[:k]]
    gt_set = {_normalize(item) for item in ground_truth}
    matched_gt = set()
    for item in top_k:
        for gt in gt_set:
            if gt in item or item in gt:
                matched_gt.add(gt)
    return round(len(matched_gt) / len(gt_set), 4)


def calculate_mrr(retrieved: List[str], ground_truth: List[str]) -> float:
    """Computes Mean Reciprocal Rank (1 / rank of first relevant item)."""
    if not ground_truth:
        return 1.0
    gt_set = {_normalize(item) for item in ground_truth}
    for rank, item in enumerate(retrieved, start=1):
        norm_item = _normalize(item)
        if any(gt in norm_item or norm_item in gt for gt in gt_set):
            return round(1.0 / rank, 4)
    return 0.0


def calculate_duplicate_rate(retrieved: List[str]) -> float:
    """Computes proportion of duplicate items in retrieved list."""
    if not retrieved:
        return 0.0
    normalized = [_normalize(item) for item in retrieved]
    unique_count = len(set(normalized))
    duplicates = len(normalized) - unique_count
    return round(duplicates / len(normalized), 4)


def calculate_irrelevant_rate(retrieved: List[str], known_irrelevant: List[str]) -> float:
    """Computes proportion of retrieved items that match known distractors."""
    if not retrieved or not known_irrelevant:
        return 0.0
    norm_retrieved = [_normalize(item) for item in retrieved]
    irr_set = {_normalize(item) for item in known_irrelevant}
    irrelevant_hits = 0
    for item in norm_retrieved:
        if any(irr in item or item in irr for irr in irr_set):
            irrelevant_hits += 1
    return round(irrelevant_hits / len(norm_retrieved), 4)
