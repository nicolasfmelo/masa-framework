from __future__ import annotations

import ast
import json
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol
from uuid import uuid4

from models import ExperimentResult, StructuralTask


ArchitectureKey = Literal["masa", "baseline"]

IGNORED_PATH_PARTS = {".venv", "__pycache__"}
IGNORED_SUFFIXES = {".pyc"}


class StructureModel(Protocol):
    def complete(self, prompt: str) -> str:
        """Return a JSON string with ranked_files, predicted_edges and target_layer."""


@dataclass
class StructuralPrediction:
    ranked_files: list[str]
    predicted_edges: list[tuple[str, str]]
    target_layer: str
    raw_response: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranked_files": self.ranked_files,
            "predicted_edges": [list(edge) for edge in self.predicted_edges],
            "target_layer": self.target_layer,
            "raw_response": self.raw_response,
        }


def _catalog_architecture_key(architecture: str) -> ArchitectureKey:
    if architecture == "baseline":
        return "baseline"
    if architecture == "masa-full":
        return "masa"
    raise ValueError(f"Unsupported architecture for structure-only runner: {architecture}")


def _iter_source_files(codebase_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(codebase_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_PATH_PARTS for part in path.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        files.append(path)
    return files


def build_directory_tree(codebase_root: Path) -> str:
    codebase_root = codebase_root.resolve()

    def render_dir(directory: Path, prefix: str = "") -> list[str]:
        children = [
            child for child in sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
            if child.name not in IGNORED_PATH_PARTS and child.suffix not in IGNORED_SUFFIXES
        ]
        lines: list[str] = []
        for index, child in enumerate(children):
            branch = "`-- " if index == len(children) - 1 else "|-- "
            lines.append(f"{prefix}{branch}{child.name}")
            if child.is_dir():
                extension = "    " if index == len(children) - 1 else "|   "
                lines.extend(render_dir(child, prefix + extension))
        return lines

    tree_lines = [codebase_root.name]
    tree_lines.extend(render_dir(codebase_root))
    return "\n".join(tree_lines)


def _format_args(arguments: ast.arguments) -> str:
    rendered: list[str] = []
    positional = list(arguments.posonlyargs) + list(arguments.args)
    defaults = [None] * (len(positional) - len(arguments.defaults)) + list(arguments.defaults)

    for arg, default in zip(positional, defaults):
        annotation = f": {ast.unparse(arg.annotation)}" if arg.annotation is not None else ""
        default_text = f" = {ast.unparse(default)}" if default is not None else ""
        rendered.append(f"{arg.arg}{annotation}{default_text}")

    if arguments.vararg is not None:
        rendered.append(f"*{arguments.vararg.arg}")

    for kwarg, default in zip(arguments.kwonlyargs, arguments.kw_defaults):
        annotation = f": {ast.unparse(kwarg.annotation)}" if kwarg.annotation is not None else ""
        default_text = f" = {ast.unparse(default)}" if default is not None else ""
        rendered.append(f"{kwarg.arg}{annotation}{default_text}")

    if arguments.kwarg is not None:
        rendered.append(f"**{arguments.kwarg.arg}")

    return ", ".join(rendered)


def extract_constructor_signatures(codebase_root: Path) -> list[str]:
    signatures: list[str] = []

    for file_path in _iter_source_files(codebase_root):
        if file_path.suffix != ".py":
            continue

        relative_path = file_path.relative_to(codebase_root).as_posix()
        module = ast.parse(file_path.read_text(encoding="utf-8"))

        for node in module.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                args = _format_args(node.args)
                return_annotation = (
                    f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
                )
                signatures.append(f"{relative_path}::{node.name}({args}){return_annotation}")
                continue

            if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
                continue

            init_method = next(
                (
                    member for member in node.body
                    if isinstance(member, ast.FunctionDef) and member.name == "__init__"
                ),
                None,
            )
            if init_method is None:
                signatures.append(f"{relative_path}::{node.name}.__init__()")
                continue

            args = _format_args(init_method.args)
            signatures.append(f"{relative_path}::{node.name}.__init__({args})")

    return signatures


def _available_relative_files(codebase_root: Path) -> list[str]:
    return [
        path.relative_to(codebase_root).as_posix()
        for path in _iter_source_files(codebase_root)
    ]


def _normalize_predicted_path(candidate: str, available_files: list[str]) -> str:
    normalized = candidate.strip()
    if not normalized:
        return normalized
    if normalized in available_files:
        return normalized

    suffix_matches = [path for path in available_files if path.endswith(normalized)]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    basename_matches = [path for path in available_files if Path(path).name == Path(normalized).name]
    if len(basename_matches) == 1:
        return basename_matches[0]

    return normalized


def normalize_prediction(prediction: StructuralPrediction, available_files: list[str]) -> StructuralPrediction:
    ranked_files = [
        _normalize_predicted_path(path, available_files)
        for path in prediction.ranked_files
    ]
    predicted_edges = [
        (
            _normalize_predicted_path(source, available_files),
            _normalize_predicted_path(target, available_files),
        )
        for source, target in prediction.predicted_edges
    ]

    return StructuralPrediction(
        ranked_files=ranked_files,
        predicted_edges=predicted_edges,
        target_layer=prediction.target_layer,
        raw_response=prediction.raw_response,
    )


def _extract_json_object(raw_response: str) -> dict[str, Any]:
    stripped = raw_response.strip()

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model response did not contain a valid JSON object.")
        return json.loads(stripped[start : end + 1])


def parse_prediction(raw_response: str) -> StructuralPrediction:
    payload = _extract_json_object(raw_response)

    ranked_files = payload.get("ranked_files", [])
    predicted_edges = payload.get("predicted_edges", [])
    target_layer = payload.get("target_layer", "")

    if not isinstance(ranked_files, list) or not all(isinstance(item, str) for item in ranked_files):
        raise ValueError("ranked_files must be a list[str].")
    if not isinstance(predicted_edges, list):
        raise ValueError("predicted_edges must be a list.")
    if not isinstance(target_layer, str) or not target_layer.strip():
        raise ValueError("target_layer must be a non-empty string.")

    normalized_edges: list[tuple[str, str]] = []
    for edge in predicted_edges:
        if (
            not isinstance(edge, list)
            or len(edge) != 2
            or not all(isinstance(item, str) for item in edge)
        ):
            raise ValueError("Each predicted edge must be a [source, target] string pair.")
        normalized_edges.append((edge[0], edge[1]))

    return StructuralPrediction(
        ranked_files=ranked_files,
        predicted_edges=normalized_edges,
        target_layer=target_layer.strip(),
        raw_response=raw_response,
    )


def f1_score(predicted: list[str] | list[tuple[str, str]], ground_truth: list[str] | list[tuple[str, str]]) -> float:
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


class StructureOnlyRunner:
    def __init__(self, catalog_path: str | Path):
        self.catalog_path = Path(catalog_path)
        self.catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))

    def load_structural_task(
        self,
        *,
        task_id: str,
        architecture: str,
        codebase_root: str | Path,
    ) -> StructuralTask:
        codebase_path = Path(codebase_root)
        architecture_key = _catalog_architecture_key(architecture)

        matching_task = next(
            (
                task for task in self.catalog["tasks"]
                if task["task_id"] == task_id and task["condition"] == "structure-only"
            ),
            None,
        )
        if matching_task is None:
            raise ValueError(f"Structure-only task not found: {task_id}")

        ground_truth = matching_task["ground_truth"][architecture_key]
        return StructuralTask(
            task_id=matching_task["task_id"],
            case=self.catalog["case"],
            condition=matching_task["condition"],
            description=matching_task["description"],
            directory_tree=build_directory_tree(codebase_path),
            constructor_signatures=extract_constructor_signatures(codebase_path),
            ground_truth_files=ground_truth["files"],
            ground_truth_edges=[tuple(edge) for edge in ground_truth["edges"]],
            target_layer=ground_truth["target_layer"],
            difficulty=matching_task["difficulty"],
        )

    def build_prompt(self, task: StructuralTask) -> str:
        signature_block = "\n".join(f"- {signature}" for signature in task.constructor_signatures)

        return textwrap.dedent(
            f"""
            You are evaluating codebase cognizability under a structure-only condition.
            You MUST rely only on the directory tree and public constructor/function signatures.

            Task ID: {task.task_id}
            Case: {task.case}
            Difficulty: {task.difficulty}

            Change request:
            {task.description}

            Directory tree:
            {task.directory_tree}

            Public constructor/function signatures:
            {signature_block}

            Return JSON only with this exact schema:
            {{
              "ranked_files": ["path/file.py", "path/other.py"],
              "predicted_edges": [["caller.py", "callee.py"]],
              "target_layer": "engines"
            }}

            Rules:
            - ranked_files must be ordered from most likely to least likely.
            - predicted_edges should contain only direct collaborator relationships relevant to the task.
            - target_layer must be a single layer name.
            - Do not include markdown fences or explanation.
            """
        ).strip()

    def run(
        self,
        *,
        model: StructureModel,
        task_id: str,
        architecture: str,
        codebase_root: str | Path,
        model_id: str,
        model_tier: str,
        provider: str = "bedrock",
    ) -> tuple[StructuralTask, StructuralPrediction, ExperimentResult]:
        task = self.load_structural_task(
            task_id=task_id,
            architecture=architecture,
            codebase_root=codebase_root,
        )
        prompt = self.build_prompt(task)
        available_files = _available_relative_files(Path(codebase_root))

        started_at = time.perf_counter()
        raw_response = model.complete(prompt)
        elapsed = time.perf_counter() - started_at

        prediction = normalize_prediction(parse_prediction(raw_response), available_files)
        retrieval_f1 = f1_score(prediction.ranked_files, task.ground_truth_files)
        graph_f1 = f1_score(prediction.predicted_edges, task.ground_truth_edges)
        layer_match = prediction.target_layer == task.target_layer

        result = ExperimentResult(
            run_id=f"struct-{task.task_id}-{uuid4().hex[:8]}",
            condition="structure-only",
            architecture=architecture,
            codebase=Path(codebase_root).name,
            language="python",
            model_id=model_id,
            model_tier=model_tier,
            provider=provider,
            task_id=task.task_id,
            difficulty=task.difficulty,
            retrieval_f1=retrieval_f1,
            graph_f1=graph_f1,
            tool_calls=0,
            wall_time_seconds=round(elapsed, 6),
            notes=(
                f"target_layer_expected={task.target_layer}; "
                f"target_layer_predicted={prediction.target_layer}; "
                f"target_layer_match={layer_match}"
            ),
        )
        return task, prediction, result


__all__ = [
    "StructuralPrediction",
    "StructureModel",
    "StructureOnlyRunner",
    "build_directory_tree",
    "extract_constructor_signatures",
    "f1_score",
    "parse_prediction",
]
