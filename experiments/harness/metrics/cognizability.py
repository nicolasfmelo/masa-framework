from __future__ import annotations

from typing import Iterable


def f1_score(
    predicted: Iterable[str] | Iterable[tuple[str, str]],
    ground_truth: Iterable[str] | Iterable[tuple[str, str]],
) -> float:
    predicted_set = set(predicted)
    truth_set = set(ground_truth)

    if not predicted_set and not truth_set:
        return 1.0
    if not predicted_set or not truth_set:
        return 0.0

    true_positives = len(predicted_set & truth_set)
    precision = true_positives / len(predicted_set)
    recall = true_positives / len(truth_set)

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def new_violation_count(before_count: int, after_count: int) -> int:
    return max(0, after_count - before_count)


def architectural_compliance_score(before_count: int, after_count: int) -> float:
    """
    Operational approximation for V in the harness.

    The study definition is `1 - normalized_new_violations(...)`.
    Since we currently count violations rather than enumerating all possible checks,
    we score compliance as an inverse penalty over *new* violations only.
    This keeps pre-existing baseline violations from automatically zeroing the score.
    """
    return 1.0 / (1.0 + new_violation_count(before_count, after_count))


def exploration_efficiency(backtrack_events: int, total_file_reads: int) -> float:
    if total_file_reads <= 0:
        return 1.0
    efficiency = 1.0 - (backtrack_events / total_file_reads)
    return max(0.0, min(1.0, efficiency))


def c_core(retrieval_f1: float, graph_f1: float, compliance_score: float) -> float:
    return (retrieval_f1 + graph_f1 + compliance_score) / 3.0


def c_operational(c_core_score: float, exploration_efficiency_score: float) -> float:
    return 0.8 * c_core_score + 0.2 * exploration_efficiency_score
