from __future__ import annotations

from pathlib import Path

from linter.track_a.checks import (
    check_boundary_types,
    check_canonical_structure,
    check_dependency_dag,
    check_semantic_specificity,
)
from linter.track_b.checks import (
    check_anemic_delivery,
    check_data_dressing,
    check_id_encapsulation,
    check_semantic_error_handling,
    check_static_dependency_tracing,
)
from linter.types import LintReport, LinterViolation


class ArchitectureLinter:
    def lint(self, codebase_root: str | Path) -> LintReport:
        codebase_path = Path(codebase_root)
        violations: list[LinterViolation] = []

        violations.extend(check_semantic_specificity(codebase_path))
        violations.extend(check_canonical_structure(codebase_path))
        violations.extend(check_dependency_dag(codebase_path))
        violations.extend(check_boundary_types(codebase_path))

        violations.extend(check_data_dressing(codebase_path))
        violations.extend(check_static_dependency_tracing(codebase_path))
        violations.extend(check_anemic_delivery(codebase_path))
        violations.extend(check_semantic_error_handling(codebase_path))
        violations.extend(check_id_encapsulation(codebase_path))

        violations.sort(key=lambda violation: (violation.file, violation.line, violation.code))
        return LintReport(codebase=codebase_path.as_posix(), violations=violations)


__all__ = ["ArchitectureLinter", "LintReport", "LinterViolation"]
