from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


Architecture = Literal["masa-full", "baseline", "ablation-ar1", "ablation-ar2",
                       "ablation-ar3", "ablation-ar4", "ablation-ar5",
                       "perturb-sp1", "perturb-sp2", "perturb-sp3"]

Condition = Literal["structure-only", "full-edit"]

ModelTier = Literal["small", "mid", "frontier"]

Difficulty = Literal["low", "medium", "high"]


@dataclass
class StructuralTask:
    """Input contract for the structure-only runner (C1)."""
    task_id: str
    case: str                             # "case-l" | "case-m" | "case-h"
    condition: Condition
    description: str
    directory_tree: str
    constructor_signatures: list[str]
    ground_truth_files: list[str]
    ground_truth_edges: list[tuple[str, str]]
    target_layer: str
    difficulty: Difficulty = "low"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "StructuralTask":
        return cls(**payload)


@dataclass
class ExperimentResult:
    """Unified output record for every experimental run."""
    run_id: str
    condition: Condition
    architecture: Architecture
    codebase: str                         # e.g. "case-l/masa", "case-l/baseline"
    language: str                         # "python"
    model_id: str                         # Bedrock model ARN / ID
    model_tier: ModelTier
    provider: str                         # "bedrock"
    task_id: str
    difficulty: Difficulty

    # Core metrics (None when not applicable to the condition)
    retrieval_f1: float | None = None     # R  – structure-only
    graph_f1: float | None = None         # G  – structure-only
    violation_count: int | None = None    # V  – full-edit
    pass_rate: float | None = None        # functional correctness – full-edit

    # Operational metrics
    tool_calls: int | None = None
    wall_time_seconds: float | None = None
    estimated_cost_usd: float | None = None

    # Free-form log for debugging
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "ExperimentResult":
        return cls(**payload)
