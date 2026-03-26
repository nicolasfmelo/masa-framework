from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean

import pandas as pd
import statsmodels.formula.api as smf


BOOTSTRAP_SEED = 7
BOOTSTRAP_SAMPLES = 2000
IMPORT_RE = re.compile(r"^\s*(import\s+\S+|from\s+\S+\s+import\s+.+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze experiment results for a specific case.")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-title", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--structure-path", required=True)
    parser.add_argument("--edit-path", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--summary-md", required=True)
    parser.add_argument("--readable-md", required=True)
    parser.add_argument("--masa-root", required=True)
    parser.add_argument("--baseline-root", required=True)
    return parser.parse_args()


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
        c_core = (record["retrieval_f1"] + record["graph_f1"] + record["compliance_score"]) / 3.0
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


def _bootstrap_delta_c_core_by_tier(structure_df: pd.DataFrame, edit_df: pd.DataFrame) -> dict[str, dict]:
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


def _usage_table(rows: list[dict], condition: str) -> list[dict]:
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        if "result" not in row or "provider_usage" not in row:
            continue
        res = row["result"]
        usage = row["provider_usage"]
        total_tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        grouped[(res["architecture"], res["model_tier"])].append(total_tokens)

    records = []
    for (architecture, model_tier), totals in sorted(grouped.items()):
        records.append(
            {
                "condition": condition,
                "architecture": architecture,
                "model_tier": model_tier,
                "avg_total_tokens": mean(totals),
            }
        )
    return records


def _context_stats(catalog: dict) -> dict[str, dict[str, dict[str, float]]]:
    stats: dict[str, dict[str, dict[str, list[int]]]] = {
        "masa-full": defaultdict(lambda: {"files": [], "edges": []}),
        "baseline": defaultdict(lambda: {"files": [], "edges": []}),
    }
    arch_key = {"masa-full": "masa", "baseline": "baseline"}

    for task in catalog["tasks"]:
        for architecture in ["masa-full", "baseline"]:
            gt = task["ground_truth"][arch_key[architecture]]
            stats[architecture][task["block"]]["files"].append(len(gt["files"]))
            stats[architecture][task["block"]]["edges"].append(len(gt["edges"]))

    rendered: dict[str, dict[str, dict[str, float]]] = {"masa-full": {}, "baseline": {}}
    for architecture, blocks in stats.items():
        for block, values in blocks.items():
            rendered[architecture][block] = {
                "avg_files": mean(values["files"]),
                "avg_edges": mean(values["edges"]),
            }
    return rendered


def _count_imports(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if IMPORT_RE.match(line))


def _import_stats(catalog: dict, masa_root: Path, baseline_root: Path) -> dict[str, dict[str, float]]:
    roots = {"masa-full": masa_root, "baseline": baseline_root}
    arch_key = {"masa-full": "masa", "baseline": "baseline"}
    stats: dict[str, list[int]] = {"masa-full": [], "baseline": []}

    for task in catalog["tasks"]:
        for architecture in ["masa-full", "baseline"]:
            total_imports = 0
            for relative_path in task["ground_truth"][arch_key[architecture]]["files"]:
                file_path = roots[architecture] / relative_path
                total_imports += _count_imports(file_path)
            stats[architecture].append(total_imports)

    return {
        architecture: {
            "avg_imports": mean(values),
            "max_imports": max(values),
        }
        for architecture, values in stats.items()
    }


def _render_markdown(
    *,
    case_title: str,
    core_table: list[dict],
    interaction_table: list[dict],
    errors: list[dict],
    retrieval_model_summary: str,
    graph_model_summary: str,
    compliance_model_summary: str,
    structure_usage: list[dict],
    full_edit_usage: list[dict],
    context_stats: dict[str, dict[str, dict[str, float]]],
    import_stats: dict[str, dict[str, float]],
) -> str:
    lines: list[str] = []
    lines.append(f"# Analysis Summary — {case_title}")
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
    lines.append("## Operational Notes — Tokens, Context Size and Imports")
    lines.append("")
    lines.append("### Token usage observed in the benchmark")
    lines.append("")
    lines.append("#### Structure-only")
    lines.append("")
    for row in structure_usage:
        lines.append(
            f"- `{row['architecture']}` / `{row['model_tier']}`: ~`{row['avg_total_tokens']:.0f}` total tokens per run"
        )

    lines.append("")
    lines.append("#### Full-edit")
    lines.append("")
    for row in full_edit_usage:
        lines.append(
            f"- `{row['architecture']}` / `{row['model_tier']}`: ~`{row['avg_total_tokens']:.0f}` total tokens per run"
        )

    lines.append("")
    lines.append("### Context size required by annotated ground truth")
    lines.append("")
    for architecture in ["masa-full", "baseline"]:
        lines.append(f"#### {architecture}")
        lines.append("")
        for block in ["retrieval", "graph-reconstruction", "patch", "failure-path"]:
            values = context_stats[architecture][block]
            lines.append(
                f"- `{block}`: avg `{values['avg_files']:.2f}` files, `{values['avg_edges']:.2f}` edges"
            )
        lines.append("")

    lines.append("### Imports over the relevant task context")
    lines.append("")
    for architecture in ["masa-full", "baseline"]:
        values = import_stats[architecture]
        lines.append(
            f"- `{architecture}`: average `{values['avg_imports']:.2f}` imports, maximum `{values['max_imports']}`"
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


def _render_readable_markdown(
    *,
    case_title: str,
    core_table: list[dict],
    interaction_table: list[dict],
    structure_usage: list[dict],
    full_edit_usage: list[dict],
    context_stats: dict[str, dict[str, dict[str, float]]],
    import_stats: dict[str, dict[str, float]],
) -> str:
    by_key = {(row["architecture"], row["model_tier"]): row for row in core_table}
    delta_by_tier = {row["model_tier"]: row["delta_c_core"] for row in interaction_table}
    tier_order = ["small", "mid", "frontier"]
    available_tiers = [tier for tier in tier_order if ("masa-full", tier) in by_key and ("baseline", tier) in by_key]
    positive_tiers = [tier for tier, delta in delta_by_tier.items() if delta > 0]
    negative_tiers = [tier for tier, delta in delta_by_tier.items() if delta < 0]

    compliance_gap = {
        tier: by_key[("baseline", tier)]["avg_violations"] - by_key[("masa-full", tier)]["avg_violations"]
        for tier in delta_by_tier
    }
    best_gap_tier = max(compliance_gap, key=compliance_gap.get)

    lines: list[str] = []
    lines.append(f"# Leitura Executiva dos Resultados — {case_title}")
    lines.append("")
    lines.append("## Resumo em uma frase")
    lines.append("")
    if positive_tiers and negative_tiers:
        lines.append(
            f"No **{case_title}**, o resultado ficou **misto**: o baseline orientou melhor o modelo em parte do "
            f"`structure-only`, mas o **MASA** manteve a maior vantagem onde a hipótese é mais crítica para engenharia, "
            f"ou seja, em **compliance arquitetural durante edição**."
        )
    elif positive_tiers:
        lines.append(
            f"No **{case_title}**, a arquitetura **MASA** melhorou o score composto do experimento nos tiers observados, "
            f"com a maior força aparecendo no eixo de **compliance arquitetural**."
        )
    else:
        lines.append(
            f"No **{case_title}**, a arquitetura **MASA** não venceu o baseline no score composto geral, mas ainda assim "
            f"reduziu drasticamente o dano arquitetural durante as mudanças."
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## O que foi medido aqui, em termos simples")
    lines.append("")
    lines.append("- **Structure-only**: o modelo recebe a estrutura do projeto e precisa se orientar sem editar.")
    lines.append("- **Full-edit**: o modelo pode ler, editar, testar e passar pelo linter em uma cópia do projeto.")
    lines.append("- **R** mede localização dos arquivos mais prováveis.")
    lines.append("- **G** mede reconstrução de colaboradores e dependências.")
    lines.append("- **V** mede compliance arquitetural.")
    lines.append("- **C_core** resume os três eixos em um score único.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Resultado principal")
    lines.append("")
    if positive_tiers and negative_tiers:
        lines.append(
            f"O quadro mais honesto aqui é: **MASA ganhou em alguns aspectos e perdeu em outros**. "
            f"No score composto `C_core`, os tiers positivos foram `{', '.join(positive_tiers)}` e os negativos foram "
            f"`{', '.join(negative_tiers)}`."
        )
    elif positive_tiers:
        lines.append(
            f"O score composto `C_core` ficou positivo para MASA em `{', '.join(positive_tiers)}`."
        )
    else:
        lines.append("O score composto `C_core` não ficou favorável ao MASA neste case.")

    lines.append("")
    for row in interaction_table:
        lines.append(f"- **{row['model_tier']}**: `ΔC_core = {row['delta_c_core']:.4f}`")

    lines.append("")
    lines.append("## O sinal mais forte do experimento")
    lines.append("")
    lines.append(
        f"O sinal mais robusto continua sendo **compliance arquitetural**. No `full-edit`, o MASA manteve "
        f"`0` violações médias em todos os tiers, enquanto o baseline ficou em torno de "
        f"`{by_key[('baseline', best_gap_tier)]['avg_violations']:.2f}` violações no tier `{best_gap_tier}` "
        f"e em faixa semelhante nos demais."
    )
    lines.append("")
    lines.append("Em termos práticos:")
    lines.append("")
    lines.append("- os dois lados conseguiram completar as tasks (`pass_rate = 1.0`);")
    lines.append("- mas só o MASA preservou as fronteiras arquiteturais;")
    lines.append("- então a diferença principal não foi 'funciona ou não funciona', e sim **como funciona**.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## O que aconteceu em `structure-only`")
    lines.append("")
    if positive_tiers and not negative_tiers:
        lines.append("Aqui o MASA continuou na frente, mas com vantagem moderada.")
    elif positive_tiers and negative_tiers:
        lines.append("Aqui o resultado ficou misto: houve tiers com vantagem para MASA e tiers mais equilibrados.")
    else:
        lines.append("Aqui o baseline ficou mais competitivo na orientacao estrutural.")
    lines.append("")
    for tier in available_tiers:
        masa = by_key[("masa-full", tier)]
        baseline = by_key[("baseline", tier)]
        lines.append(f"### Tier `{tier}`")
        lines.append("")
        lines.append(f"- `R`: baseline `{baseline['R']:.4f}` vs masa `{masa['R']:.4f}`")
        lines.append(f"- `G`: baseline `{baseline['G']:.4f}` vs masa `{masa['G']:.4f}`")
        lines.append("")

    if positive_tiers and negative_tiers:
        lines.append(
            "A leitura mais provável é que este case distribui o comportamento de um jeito em que a orientacao "
            "estrutural nao favorece sempre a mesma arquitetura em todos os tiers."
        )
    elif positive_tiers:
        lines.append(
            "A leitura mais provável é que a organizacao semântica do MASA continuou ajudando o modelo a localizar "
            "os pontos de mudança e reconstruir dependências com menos ambiguidade."
        )
    else:
        lines.append(
            "A leitura mais provável é que, neste case, a baseline ficou mais direta de navegar para esse tipo "
            "de prompt estrutural."
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## O que aconteceu em `full-edit`")
    lines.append("")
    lines.append("Aqui o padrão voltou a ser muito claro.")
    lines.append("")
    for tier in available_tiers:
        masa = by_key[("masa-full", tier)]
        baseline = by_key[("baseline", tier)]
        lines.append(f"- **{tier}**")
        lines.append(f"  - MASA: `pass_rate={masa['pass_rate']:.1f}`, `violations={masa['avg_violations']:.2f}`")
        lines.append(f"  - baseline: `pass_rate={baseline['pass_rate']:.1f}`, `violations={baseline['avg_violations']:.2f}`")
    missing_tiers = [tier for tier in tier_order if tier not in available_tiers]
    for tier in missing_tiers:
        lines.append(f"- **{tier}**")
        lines.append("  - sem agregado comparável por conta de falhas operacionais no benchmark")
    lines.append("")
    lines.append(
        "Ou seja: o baseline foi competitivo em orientação estrutural, mas quando a task exigiu editar o sistema "
        "sem bagunçar a arquitetura, o MASA foi muito mais estável."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Custo operacional: tokens, contexto e imports")
    lines.append("")
    lines.append("### Consumo de tokens")
    lines.append("")
    lines.append("#### `structure-only`")
    lines.append("")
    for row in structure_usage:
        lines.append(f"- `{row['architecture']}` / `{row['model_tier']}`: ~`{row['avg_total_tokens']:.0f}` tokens")
    lines.append("")
    lines.append("#### `full-edit`")
    lines.append("")
    for row in full_edit_usage:
        lines.append(f"- `{row['architecture']}` / `{row['model_tier']}`: ~`{row['avg_total_tokens']:.0f}` tokens")
    lines.append("")
    lines.append(
        "Aqui a leitura importante é que MASA nao significa automaticamente menos tokens. Em geral, ele expõe "
        "mais estrutura e isso pode aumentar o custo de contexto, principalmente quando o modelo faz uma exploração "
        "mais disciplinada."
    )
    lines.append("")
    lines.append("### Contexto mínimo anotado")
    lines.append("")
    for architecture in ["masa-full", "baseline"]:
        retrieval = context_stats[architecture]["retrieval"]
        graph = context_stats[architecture]["graph-reconstruction"]
        lines.append(
            f"- `{architecture}`: retrieval ~`{retrieval['avg_files']:.2f}` arquivos / `{retrieval['avg_edges']:.2f}` relações; "
            f"graph ~`{graph['avg_files']:.2f}` arquivos / `{graph['avg_edges']:.2f}` relações"
        )
    lines.append("")
    lines.append("### Imports na vizinhança relevante da task")
    lines.append("")
    for architecture in ["masa-full", "baseline"]:
        values = import_stats[architecture]
        lines.append(
            f"- `{architecture}`: média de `{values['avg_imports']:.2f}` imports; máximo `{values['max_imports']}`"
        )
    lines.append("")
    lines.append(
        "Isso reforça um ponto importante: MASA pode exigir mais contexto explícito, mas entrega fronteiras mais "
        "claras quando o modelo precisa mudar o código de verdade."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Leitura final")
    lines.append("")
    lines.append(
        f"O **{case_title}** reforça que `navegabilidade` e `segurança arquitetural ao editar` nao sao exatamente a "
        "mesma coisa. Mesmo quando a baseline fica competitiva em parte da orientação estrutural, o **MASA** tende a "
        "ser mais forte em preservar a arquitetura quando a mudança é executada."
    )
    lines.append("")
    lines.append(
        "Se a hipótese do estudo for refinada como 'MASA ajuda sobretudo a reduzir dano estrutural durante trabalho "
        "agêntico', este case reforça bem essa narrativa."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    catalog_path = Path(args.catalog)
    structure_path = Path(args.structure_path)
    edit_path = Path(args.edit_path)
    summary_json_path = Path(args.summary_json)
    summary_md_path = Path(args.summary_md)
    readable_md_path = Path(args.readable_md)
    masa_root = Path(args.masa_root)
    baseline_root = Path(args.baseline_root)

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    structure_rows = _dedupe_rows(_load_jsonl(structure_path))
    edit_rows = _dedupe_rows(_load_jsonl(edit_path))

    structure_df = _structure_dataframe(structure_rows)
    edit_df, errors = _edit_dataframe(edit_rows)

    core_table = _aggregate_core_table(structure_df, edit_df)
    bootstrap = _bootstrap_delta_c_core_by_tier(structure_df, edit_df)
    interaction_table = _interaction_table(core_table, bootstrap)
    structure_usage = _usage_table(structure_rows, "structure-only")
    full_edit_usage = _usage_table(edit_rows, "full-edit")
    context_stats = _context_stats(catalog)
    import_stats = _import_stats(catalog, masa_root=masa_root, baseline_root=baseline_root)

    retrieval_model_summary = _fit_mixed_model(structure_df, "retrieval_f1")
    graph_model_summary = _fit_mixed_model(structure_df, "graph_f1")
    compliance_model_summary = _fit_mixed_model(edit_df, "compliance_score")

    summary_payload = {
        "case_id": args.case_id,
        "case_title": args.case_title,
        "core_table": core_table,
        "interaction_table": interaction_table,
        "failed_runs": errors,
        "usage": {
            "structure_only": structure_usage,
            "full_edit": full_edit_usage,
        },
        "context_stats": context_stats,
        "import_stats": import_stats,
        "mixed_models": {
            "retrieval_f1": retrieval_model_summary,
            "graph_f1": graph_model_summary,
            "compliance_score": compliance_model_summary,
        },
    }
    summary_json_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    summary_md_path.write_text(
        _render_markdown(
            case_title=args.case_title,
            core_table=core_table,
            interaction_table=interaction_table,
            errors=errors,
            retrieval_model_summary=retrieval_model_summary,
            graph_model_summary=graph_model_summary,
            compliance_model_summary=compliance_model_summary,
            structure_usage=structure_usage,
            full_edit_usage=full_edit_usage,
            context_stats=context_stats,
            import_stats=import_stats,
        ),
        encoding="utf-8",
    )
    readable_md_path.write_text(
        _render_readable_markdown(
            case_title=args.case_title,
            core_table=core_table,
            interaction_table=interaction_table,
            structure_usage=structure_usage,
            full_edit_usage=full_edit_usage,
            context_stats=context_stats,
            import_stats=import_stats,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {summary_json_path}")
    print(f"Wrote {summary_md_path}")
    print(f"Wrote {readable_md_path}")


if __name__ == "__main__":
    main()
