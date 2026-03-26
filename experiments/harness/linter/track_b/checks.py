from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from linter.types import LinterViolation


def _iter_python_files(codebase_root: Path) -> Iterable[Path]:
    for path in sorted(codebase_root.rglob("*.py")):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        yield path


def check_data_dressing(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()
        if not (relative.startswith("src/services/") or relative.startswith("src/engines/") or relative == "app/service.py"):
            continue

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                violations.append(
                    LinterViolation(
                        code="R1",
                        file=relative,
                        line=node.lineno,
                        message="Business layer returns raw dict data instead of domain objects.",
                    )
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "vars":
                violations.append(
                    LinterViolation(
                        code="R1",
                        file=relative,
                        line=node.lineno,
                        message="Business layer serializes objects into raw dict payloads.",
                    )
                )

    return violations


def check_static_dependency_tracing(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()
        if not (relative.startswith("src/services/") or relative == "app/service.py"):
            continue

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        top_level_imports = [node for node in module.body if isinstance(node, (ast.Import, ast.ImportFrom))]
        top_level_functions = [node for node in module.body if isinstance(node, ast.FunctionDef)]

        if relative == "app/service.py" and top_level_imports and top_level_functions:
            violations.append(
                LinterViolation(
                    code="R2",
                    file=relative,
                    line=top_level_functions[0].lineno,
                    message="Service logic is wired through static module imports instead of explicit constructor injection.",
                )
            )

        for node in ast.walk(module):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if isinstance(node.func.value, ast.Name) and node.func.value.id in {"container", "services", "locator"}:
                    violations.append(
                        LinterViolation(
                            code="R2",
                            file=relative,
                            line=node.lineno,
                            message="Hidden dependency lookup detected.",
                        )
                    )
                continue

    return violations


def check_anemic_delivery(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()
        if relative not in {"app/routes.py", "src/delivery/http/handlers.py"}:
            continue

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if not isinstance(node, ast.Subscript):
                continue
            if relative == "app/routes.py" and isinstance(node.value, ast.Name) and node.value.id == "result":
                violations.append(
                    LinterViolation(
                        code="R3",
                        file=relative,
                        line=node.lineno,
                        message="Delivery layer is unpacking business data dicts directly.",
                    )
                )

    return violations


def check_semantic_error_handling(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []
    builtin_exception_names = {"ValueError", "TypeError", "KeyError", "RuntimeError"}

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()
        if not (
            relative.startswith("src/services/")
            or relative.startswith("src/engines/")
            or relative.startswith("src/integrations/")
            or relative in {"app/service.py", "app/utils.py"}
        ):
            continue

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for function_node in ast.walk(module):
            if not isinstance(function_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if function_node.name.startswith("_"):
                continue

            for node in ast.walk(function_node):
                if not isinstance(node, ast.Raise):
                    continue
                if not isinstance(node.exc, ast.Call) or not isinstance(node.exc.func, ast.Name):
                    continue
                if node.exc.func.id not in builtin_exception_names:
                    continue

                violations.append(
                    LinterViolation(
                        code="R4",
                        file=relative,
                        line=node.lineno,
                        message=f"Builtin exception '{node.exc.func.id}' leaks into business flow.",
                    )
                )

    return violations


def check_id_encapsulation(codebase_root: Path) -> list[LinterViolation]:
    violations: list[LinterViolation] = []

    for file_path in _iter_python_files(codebase_root):
        relative = file_path.relative_to(codebase_root).as_posix()
        if relative.startswith("src/domain_models/"):
            continue
        if relative != "app/models.py":
            continue

        module = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
                continue
            for arg in node.args.args:
                if arg.arg == "product_id":
                    violations.append(
                        LinterViolation(
                            code="R5",
                            file=relative,
                            line=node.lineno,
                            message="Primitive product_id crosses non-domain API without encapsulation.",
                        )
                    )

    return violations
