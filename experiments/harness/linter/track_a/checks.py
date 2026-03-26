from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from linter.types import LinterViolation


GENERIC_FILE_NAMES = {"utils.py", "service.py", "models.py", "helpers.py", "core.py"}
GENERIC_FUNCTION_NAMES = {"process_data", "handle_file", "handle", "run", "execute"}


def _iter_python_files(codebase_root: Path) -> Iterable[Path]:
    for path in sorted(codebase_root.rglob("*.py")):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        yield path


def check_semantic_specificity(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()

        if file_path.name in GENERIC_FILE_NAMES:
            violations.append(
                LinterViolation(
                    code="S1",
                    file=relative,
                    line=1,
                    message=f"Generic filename '{file_path.name}' weakens structural signal.",
                )
            )

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in module.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in GENERIC_FUNCTION_NAMES:
                violations.append(
                    LinterViolation(
                        code="S1",
                        file=relative,
                        line=node.lineno,
                        message=f"Generic function name '{node.name}' weakens structural signal.",
                    )
                )

    return violations


def check_canonical_structure(codebase_root: Path) -> list[LinterViolation]:
    expected_dirs = {"domain_models", "engines", "integrations", "services", "delivery"}
    top_level = {child.name for child in codebase_root.iterdir() if child.is_dir()}
    src_level = set()
    if "src" in top_level:
        src_level = {child.name for child in (codebase_root / "src").iterdir() if child.is_dir()}

    if expected_dirs.issubset(top_level) or expected_dirs.issubset(src_level):
        return []

    if codebase_root.name == "baseline":
        return [
            LinterViolation(
                code="S2",
                file=".",
                line=1,
                message="Baseline layout is non-canonical: MASA layer directories are absent.",
            )
        ]

    return [
        LinterViolation(
            code="S2",
            file=".",
            line=1,
            message="Canonical MASA layer layout is incomplete.",
        )
    ]


def check_dependency_dag(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()
        module = ast.parse(file_path.read_text(encoding="utf-8"))

        for node in module.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            imported_names = []
            if isinstance(node, ast.Import):
                imported_names = [alias.name for alias in node.names]
            elif node.module is not None:
                imported_names = [node.module]

            if relative.startswith("src/domain_models/") and any(
                name.startswith(("src.services", "src.engines", "src.integrations", "src.delivery"))
                for name in imported_names
            ):
                violations.append(
                    LinterViolation(
                        code="S3",
                        file=relative,
                        line=node.lineno,
                        message="Domain layer must not depend on upper layers.",
                    )
                )

            if relative.startswith("src/engines/") and any(name.startswith("src.delivery") for name in imported_names):
                violations.append(
                    LinterViolation(
                        code="S3",
                        file=relative,
                        line=node.lineno,
                        message="Engine layer must not import delivery layer.",
                    )
                )

            if relative.startswith("src/services/") and any(name.startswith("src.delivery") for name in imported_names):
                violations.append(
                    LinterViolation(
                        code="S3",
                        file=relative,
                        line=node.lineno,
                        message="Service layer must not import delivery layer.",
                    )
                )

    return violations


def check_boundary_types(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()
        if not (relative.startswith("src/services/") or relative.startswith("src/engines/") or relative == "app/service.py"):
            continue

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in module.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if isinstance(node.returns, ast.Name) and node.returns.id in {"dict", "Any"}:
                violations.append(
                    LinterViolation(
                        code="S4",
                        file=relative,
                        line=node.lineno,
                        message=f"Function '{node.name}' returns raw boundary type '{node.returns.id}'.",
                    )
                )

    return violations
