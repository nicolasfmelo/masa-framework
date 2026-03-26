from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol
from uuid import uuid4

from linter import ArchitectureLinter
from linter.types import LintReport
from metrics import architectural_compliance_score, c_core, c_operational, new_violation_count
from models import ExperimentResult


ArchitectureKey = Literal["masa", "baseline"]


class PatchModel(Protocol):
    def solve(self, prompt: str, tools: "PatchToolExecutor") -> str:
        """Execute a patch task using the standardized tool executor."""


@dataclass
class ToolExecutionResult:
    tool_name: str
    ok: bool
    command: str | None = None
    output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "ok": self.ok,
            "command": self.command,
            "output": self.output,
        }


@dataclass
class PatchRunArtifacts:
    prompt: str
    model_response: str
    workspace_root: str
    before_lint: LintReport
    after_lint: LintReport
    tool_results: list[ToolExecutionResult] = field(default_factory=list)
    compliance_score: float = 0.0
    c_core_score: float | None = None
    c_operational_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "model_response": self.model_response,
            "workspace_root": self.workspace_root,
            "before_lint": self.before_lint.to_dict(),
            "after_lint": self.after_lint.to_dict(),
            "tool_results": [tool.to_dict() for tool in self.tool_results],
            "compliance_score": self.compliance_score,
            "c_core_score": self.c_core_score,
            "c_operational_score": self.c_operational_score,
        }


def _catalog_architecture_key(architecture: str) -> ArchitectureKey:
    if architecture == "baseline":
        return "baseline"
    if architecture == "masa-full":
        return "masa"
    raise ValueError(f"Unsupported architecture for patch runner: {architecture}")


class PatchToolExecutor:
    def __init__(
        self,
        *,
        workspace_root: Path,
        linter: ArchitectureLinter,
        test_command: list[str] | None = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.linter = linter
        self.test_command = test_command
        self.history: list[ToolExecutionResult] = []

    def _resolve_path(self, relative_path: str) -> Path:
        target = (self.workspace_root / relative_path).resolve()
        if self.workspace_root.resolve() not in target.parents and target != self.workspace_root.resolve():
            raise ValueError(f"Path escapes workspace: {relative_path}")
        return target

    def _record(self, tool_name: str, ok: bool, command: str | None = None, output: str = "") -> ToolExecutionResult:
        result = ToolExecutionResult(tool_name=tool_name, ok=ok, command=command, output=output)
        self.history.append(result)
        return result

    def list_files(self) -> list[str]:
        files = [
            path.relative_to(self.workspace_root).as_posix()
            for path in sorted(self.workspace_root.rglob("*"))
            if path.is_file() and ".venv" not in path.parts and "__pycache__" not in path.parts
        ]
        self._record("list_files", ok=True, output="\n".join(files))
        return files

    def read_file(self, relative_path: str) -> str:
        target = self._resolve_path(relative_path)
        content = target.read_text(encoding="utf-8")
        self._record("read_file", ok=True, output=f"{relative_path}\n{content}")
        return content

    def edit_file(self, relative_path: str, new_content: str) -> None:
        target = self._resolve_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_content, encoding="utf-8")
        self._record("edit_file", ok=True, output=relative_path)

    def run_tests(self) -> ToolExecutionResult:
        command = self.test_command or ["uv", "run", "python", "-m", "compileall", "."]
        completed = subprocess.run(
            command,
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = (completed.stdout + completed.stderr).strip()
        return self._record(
            "run_tests",
            ok=completed.returncode == 0,
            command=" ".join(command),
            output=output,
        )

    def run_arch_lint(self) -> ToolExecutionResult:
        report = self.linter.lint(self.workspace_root)
        return self._record(
            "run_arch_lint",
            ok=True,
            output=json.dumps(report.to_dict(), indent=2),
        )


class PatchRunner:
    def __init__(self, catalog_path: str | Path, linter: ArchitectureLinter | None = None):
        self.catalog_path = Path(catalog_path)
        self.catalog = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        self.linter = linter or ArchitectureLinter()

    def load_patch_task(self, *, task_id: str, architecture: str) -> dict[str, Any]:
        architecture_key = _catalog_architecture_key(architecture)
        matching_task = next(
            (
                task for task in self.catalog["tasks"]
                if task["task_id"] == task_id and task["condition"] == "full-edit"
            ),
            None,
        )
        if matching_task is None:
            raise ValueError(f"Patch task not found: {task_id}")

        payload = dict(matching_task)
        payload["ground_truth"] = matching_task["ground_truth"][architecture_key]
        return payload

    def build_prompt(self, task: dict[str, Any]) -> str:
        return textwrap.dedent(
            f"""
            You are running a full-edit benchmark task.
            Use only the standardized tools exposed by the executor:
            - list_files()
            - read_file(path)
            - edit_file(path, new_content)
            - run_tests()
            - run_arch_lint()

            Task ID: {task["task_id"]}
            Case: {self.catalog["case"]}
            Difficulty: {task["difficulty"]}
            Change request:
            {task["description"]}

            Ground-truth files are hidden from you during execution.
            Your goal is to implement the requested behavior while minimizing new architectural violations.

            Reply with a short plain-text summary after you finish editing and validating.
            """
        ).strip()

    def run(
        self,
        *,
        model: PatchModel,
        task_id: str,
        architecture: str,
        codebase_root: str | Path,
        model_id: str,
        model_tier: str,
        provider: str = "bedrock",
        test_command: list[str] | None = None,
        keep_workspace: bool = False,
    ) -> tuple[dict[str, Any], PatchRunArtifacts, ExperimentResult]:
        task = self.load_patch_task(task_id=task_id, architecture=architecture)
        prompt = self.build_prompt(task)
        source_root = Path(codebase_root).resolve()

        temp_dir = Path(tempfile.mkdtemp(prefix="masa-patch-run-"))
        workspace_root = temp_dir / source_root.name
        shutil.copytree(source_root, workspace_root)

        executor = PatchToolExecutor(
            workspace_root=workspace_root,
            linter=self.linter,
            test_command=test_command,
        )

        before_lint = self.linter.lint(workspace_root)
        started_at = time.perf_counter()
        model_response = model.solve(prompt, executor)
        elapsed = time.perf_counter() - started_at
        after_lint = self.linter.lint(workspace_root)
        test_result = executor.run_tests()

        new_violations = new_violation_count(before_lint.violation_count, after_lint.violation_count)
        compliance_score = architectural_compliance_score(
            before_count=before_lint.violation_count,
            after_count=after_lint.violation_count,
        )
        pass_rate = 1.0 if test_result.ok else 0.0
        c_core_score = c_core(0.0, 0.0, compliance_score)
        c_operational_score = c_operational(c_core_score, 1.0)

        artifacts = PatchRunArtifacts(
            prompt=prompt,
            model_response=model_response,
            workspace_root=workspace_root.as_posix(),
            before_lint=before_lint,
            after_lint=after_lint,
            tool_results=list(executor.history),
            compliance_score=compliance_score,
            c_core_score=c_core_score,
            c_operational_score=c_operational_score,
        )

        result = ExperimentResult(
            run_id=f"patch-{task['task_id']}-{uuid4().hex[:8]}",
            condition="full-edit",
            architecture=architecture,
            codebase=source_root.name,
            language="python",
            model_id=model_id,
            model_tier=model_tier,
            provider=provider,
            task_id=task["task_id"],
            difficulty=task["difficulty"],
            violation_count=after_lint.violation_count,
            pass_rate=pass_rate,
            tool_calls=len(executor.history),
            wall_time_seconds=round(elapsed, 6),
            notes=(
                f"before_violation_count={before_lint.violation_count}; "
                f"after_violation_count={after_lint.violation_count}; "
                f"new_violation_count={new_violations}; "
                f"test_command={test_result.command}; "
                f"tests_ok={test_result.ok}; "
                f"compliance_score={compliance_score:.6f}"
            ),
        )

        if not keep_workspace:
            shutil.rmtree(temp_dir)

        return task, artifacts, result


__all__ = [
    "PatchModel",
    "PatchRunArtifacts",
    "PatchRunner",
    "PatchToolExecutor",
    "ToolExecutionResult",
]
