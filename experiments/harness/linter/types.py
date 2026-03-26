from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class LinterViolation:
    code: str
    file: str
    line: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LintReport:
    codebase: str
    violations: list[LinterViolation] = field(default_factory=list)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def by_code(self) -> dict[str, list[LinterViolation]]:
        grouped: dict[str, list[LinterViolation]] = {}
        for violation in self.violations:
            grouped.setdefault(violation.code, []).append(violation)
        return grouped

    def to_dict(self) -> dict:
        return {
            "codebase": self.codebase,
            "violation_count": self.violation_count,
            "violations": [violation.to_dict() for violation in self.violations],
        }
