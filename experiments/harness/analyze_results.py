from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import pandas as pd
import statsmodels.formula.api as smf


RESULTS_DIR = Path("results")
STRUCTURE_PATH = RESULTS_DIR / "full-structure.jsonl"
EDIT_PATH = RESULTS_DIR / "full-edit.jsonl"
SUMMARY_JSON_PATH = RESULTS_DIR / "analysis-summary.json"
SUMMARY_MD_PATH = RESULTS_DIR / "analysis-summary.md"

BOOTSTRAP_SEED = 7
BOOTSTRAP_SAMPLES = 2000


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    selected: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        if "result" in row:
            res = row["result"]
            key = (res["task_id"], res["architecture"], res["model_tier"])
            selected[key] = row
            continue

        key = (row["task_id"], row["architecture"], row["model_tier"])
        selected.setdefault(key, row)
    return list(selected.values())


def _structure_dataframe(rows: list[dict]) -> pd.DataFrame:
    records: list[dict] = []
    for row in rows:
        if "result" not in row:
            continue
        res = row["result"]
        records.append(
            {
                "task_id": res["task_id"],
                "architecture": res["architecture"],
                "model_tier": res["model_tier"],
                "model_id": res["model_id"],
                "difficulty": res["difficulty"],
                "retrieval_f1": res["retrieval_f1"],
                "graph_f1": res["graph_f1"],
            }
        )
    return pd.DataFrame.from_records(records)


def _edit_dataframe(rows: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    records: list[dict] = []
    errors: list[dict] = []
    for row in rows:
        if "result" not in row:
            errors.append(row)
            continue
        res = row["result"]
        artifacts = row["artifacts"]
        records.append(
            {
                "task_id": res["task_id"],
                "architecture": res["architecture"],
                "model_tier": res["model_tier"],
                "model_id": res["model_id"],
                "difficulty": res["difficulty"],
                "pass_rate": res["pass_rate"],
                "violation_count": res["violation_count"],
                "tool_calls": res["tool_calls"],
                "compliance_score": artifacts["compliance_score"],
            }
        )
    return pd.DataFrame.from_records(records), errors


def _aggregate_core_table(structure_df: pd.DataFrame, edit_df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    structure_grouped = structure_df.groupby(["architecture", "model_tier"], as_index=False).agg(
        retrieval_f1=("retrieval_f1", "mean"),
        graph_f1=("graph_f1", "mean"),
    )
    edit_grouped = edit_df.groupby(["architecture", "model_tier"], as_index=False).agg(
        compliance_score=("compliance_score", "mean"),
        pass_rate=("pass_rate", "mean"),
        violation_count=("violation_count", "mean"),
        tool_calls=("tool_calls", "mean"),
    )

    merged = structure_grouped.merge(edit_grouped, on=["architecture", "model_tier"], how="inner")
    for record in merged.to_dict(orient="records"):
        c_core = (
            record["retrieval_f1"] + record["graph_f1"] + record["compliance_score"]
        ) / 3.0
        rows.append(
            {
                "architecture": record["architecture"],
                "model_tier": record["model_tier"],
                "R": record["retrieval_f1"],
                "G": record["graph_f1"],
                "V": record["compliance_score"],
                "C_core": c_core,
                "pass_rate": record["pass_rate"],
                "avg_violations": record["violation_count"],
                "avg_tool_calls": record["tool_calls"],
            }
        )
    return sorted(rows, key=lambda row: (row["architecture"], row["model_tier"]))


def _bootstrap_delta_c_core_by_tier(
    structure_df: pd.DataFrame,
    edit_df: pd.DataFrame,
) -> dict[str, dict]:
    rng = pd.Series(range(BOOTSTRAP_SAMPLES)).sample(BOOTSTRAP_SAMPLES, random_state=BOOTSTRAP_SEED)
    tiers = sorted(structure_df["model_tier"].unique())
    results: dict[str, dict] = {}

    for tier in tiers:
        deltas: list[float] = []
        for sample_seed in rng:
            tier_structure = structure_df[structure_df["model_tier"] == tier]
            tier_edit = edit_df[edit_df["model_tier"] == tier]

            architecture_scores: dict[str, float] = {}
            for architecture in ["masa-full", "baseline"]:
                s_source = tier_structure[tier_structure["architecture"] == architecture]
                e_source = tier_edit[tier_edit["architecture"] == architecture]
                s = s_source.sample(n=len(s_source), replace=True, random_state=int(sample_seed))
                e = e_source.sample(n=len(e_source), replace=True, random_state=int(sample_seed) + 1)
                c_core = (
                    float(s["retrieval_f1"].mean())
                    + float(s["graph_f1"].mean())
                    + float(e["compliance_score"].mean())
                ) / 3.0
                architecture_scores[architecture] = c_core

            deltas.append(architecture_scores["masa-full"] - architecture_scores["baseline"])

        deltas_sorted = sorted(deltas)
        lower = deltas_sorted[int(0.025 * len(deltas_sorted))]
        upper = deltas_sorted[int(0.975 * len(deltas_sorted))]
        point_estimate = mean(deltas)
        results[tier] = {
            "delta_c_core": point_estimate,
            "ci95_lower": lower,
            "ci95_upper": upper,
        }
    return results


def _interaction_table(core_table: list[dict], bootstrap: dict[str, dict]) -> list[dict]:
    by_key = {(row["architecture"], row["model_tier"]): row for row in core_table}
    rows: list[dict] = []

    for tier in sorted({row["model_tier"] for row in core_table}):
        masa = by_key[("masa-full", tier)]
        baseline = by_key[("baseline", tier)]
        delta_c = masa["C_core"] - baseline["C_core"]
        relative_lift = delta_c / max(1e-6, 1 - baseline["C_core"])
        rows.append(
            {
                "model_tier": tier,
                "delta_c_core": delta_c,
                "relative_lift": relative_lift,
                "pass_rate_delta": masa["pass_rate"] - baseline["pass_rate"],
                "violation_delta": masa["avg_violations"] - baseline["avg_violations"],
                "ci95_lower": bootstrap[tier]["ci95_lower"],
                "ci95_upper": bootstrap[tier]["ci95_upper"],
            }
        )
    return rows


def _fit_mixed_model(df: pd.DataFrame, score_column: str) -> str:
    model = smf.mixedlm(
        f"{score_column} ~ C(architecture) * C(model_tier) + C(difficulty)",
        data=df,
        groups=df["task_id"],
        vc_formula={"model_id": "0 + C(model_id)"},
    )
    fitted = model.fit(reml=False, method="lbfgs", maxiter=200, disp=False)
    return fitted.summary().as_text()


def _render_markdown(
    *,
    core_table: list[dict],
    interaction_table: list[dict],
    errors: list[dict],
    retrieval_model_summary: str,
    graph_model_summary: str,
    compliance_model_summary: str,
) -> str:
    lines: list[str] = []
    lines.append("# Analysis Summary")
    lines.append("")
    lines.append("## Table 1 — Core Cognizability")
    lines.append("")
    lines.append("| Architecture | Tier | R | G | V | C_core | Pass Rate | Avg Violations | Avg Tool Calls |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in core_table:
        lines.append(
            f"| {row['architecture']} | {row['model_tier']} | "
            f"{row['R']:.4f} | {row['G']:.4f} | {row['V']:.4f} | {row['C_core']:.4f} | "
            f"{row['pass_rate']:.4f} | {row['avg_violations']:.4f} | {row['avg_tool_calls']:.4f} |"
        )

    lines.append("")
    lines.append("## Table 2 — Interaction and Robustness")
    lines.append("")
    lines.append("| Tier | ΔC_core | Relative Lift | Pass Rate Δ | Violation Δ | 95% CI |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for row in interaction_table:
        lines.append(
            f"| {row['model_tier']} | {row['delta_c_core']:.4f} | {row['relative_lift']:.4f} | "
            f"{row['pass_rate_delta']:.4f} | {row['violation_delta']:.4f} | "
            f"[{row['ci95_lower']:.4f}, {row['ci95_upper']:.4f}] |"
        )

    lines.append("")
    lines.append("## Failed Runs")
    lines.append("")
    if not errors:
        lines.append("- None")
    else:
        for error in errors:
            lines.append(
                f"- `{error['task_id']}` / `{error['architecture']}` / `{error['model_tier']}` — {error['error']}"
            )

    lines.append("")
    lines.append("## Mixed Model — Retrieval F1")
    lines.append("")
    lines.append("```text")
    lines.append(retrieval_model_summary)
    lines.append("```")
    lines.append("")
    lines.append("## Mixed Model — Graph F1")
    lines.append("")
    lines.append("```text")
    lines.append(graph_model_summary)
    lines.append("```")
    lines.append("")
    lines.append("## Mixed Model — Compliance Score")
    lines.append("")
    lines.append("```text")
    lines.append(compliance_model_summary)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    structure_rows = _dedupe_rows(_load_jsonl(STRUCTURE_PATH))
    edit_rows = _dedupe_rows(_load_jsonl(EDIT_PATH))

    structure_df = _structure_dataframe(structure_rows)
    edit_df, errors = _edit_dataframe(edit_rows)

    core_table = _aggregate_core_table(structure_df, edit_df)
    bootstrap = _bootstrap_delta_c_core_by_tier(structure_df, edit_df)
    interaction_table = _interaction_table(core_table, bootstrap)

    retrieval_model_summary = _fit_mixed_model(structure_df, "retrieval_f1")
    graph_model_summary = _fit_mixed_model(structure_df, "graph_f1")
    compliance_model_summary = _fit_mixed_model(edit_df, "compliance_score")

    summary_payload = {
        "core_table": core_table,
        "interaction_table": interaction_table,
        "failed_runs": errors,
        "mixed_models": {
            "retrieval_f1": retrieval_model_summary,
            "graph_f1": graph_model_summary,
            "compliance_score": compliance_model_summary,
        },
    }
    SUMMARY_JSON_PATH.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    SUMMARY_MD_PATH.write_text(
        _render_markdown(
            core_table=core_table,
            interaction_table=interaction_table,
            errors=errors,
            retrieval_model_summary=retrieval_model_summary,
            graph_model_summary=graph_model_summary,
            compliance_model_summary=compliance_model_summary,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {SUMMARY_JSON_PATH}")
    print(f"Wrote {SUMMARY_MD_PATH}")


if __name__ == "__main__":
    main()
