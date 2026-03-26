from __future__ import annotations

import argparse
import json
from pathlib import Path

from providers import BedrockProvider
from runners.patch_runner import PatchRunner
from runners.structure_only_runner import StructureOnlyRunner


def _write_jsonl(handle, payload: dict) -> None:
    handle.write(json.dumps(payload) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MASA Case L experiment tasks.")
    parser.add_argument("--catalog", default="tasks/case-l/catalog.json")
    parser.add_argument("--condition", choices=["structure-only", "full-edit"], required=True)
    parser.add_argument("--architecture", choices=["masa-full", "baseline"], required=True)
    parser.add_argument("--codebase-root", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-tier", choices=["small", "mid", "frontier"], required=True)
    parser.add_argument("--task-id", action="append", required=True)
    parser.add_argument("--results-path", required=True)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--profile-name", default="codeboost")
    parser.add_argument("--region-name", default="us-east-1")
    parser.add_argument("--test-command", nargs="*")
    parser.add_argument("--keep-workspace", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    provider = BedrockProvider(
        model_id=args.model_id,
        profile_name=args.profile_name,
        region_name=args.region_name,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    results_path = Path(args.results_path)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    with results_path.open("a", encoding="utf-8") as handle:
        if args.condition == "structure-only":
            runner = StructureOnlyRunner(args.catalog)
            for task_id in args.task_id:
                try:
                    task, prediction, result = runner.run(
                        model=provider,
                        task_id=task_id,
                        architecture=args.architecture,
                        codebase_root=args.codebase_root,
                        model_id=args.model_id,
                        model_tier=args.model_tier,
                    )
                    _write_jsonl(
                        handle,
                        {
                            "task": task.to_dict(),
                            "prediction": prediction.to_dict(),
                            "result": result.to_dict(),
                            "provider_usage": provider.last_usage.to_dict(),
                        },
                    )
                except Exception as exc:
                    _write_jsonl(
                        handle,
                        {
                            "task_id": task_id,
                            "condition": args.condition,
                            "architecture": args.architecture,
                            "model_id": args.model_id,
                            "model_tier": args.model_tier,
                            "error": str(exc),
                            "provider_usage": provider.last_usage.to_dict(),
                        },
                    )
        else:
            runner = PatchRunner(args.catalog)
            for task_id in args.task_id:
                try:
                    task, artifacts, result = runner.run(
                        model=provider,
                        task_id=task_id,
                        architecture=args.architecture,
                        codebase_root=args.codebase_root,
                        model_id=args.model_id,
                        model_tier=args.model_tier,
                        test_command=args.test_command,
                        keep_workspace=args.keep_workspace,
                    )
                    _write_jsonl(
                        handle,
                        {
                            "task": task,
                            "artifacts": artifacts.to_dict(),
                            "result": result.to_dict(),
                            "provider_usage": provider.last_usage.to_dict(),
                        },
                    )
                except Exception as exc:
                    _write_jsonl(
                        handle,
                        {
                            "task_id": task_id,
                            "condition": args.condition,
                            "architecture": args.architecture,
                            "model_id": args.model_id,
                            "model_tier": args.model_tier,
                            "error": str(exc),
                            "provider_usage": provider.last_usage.to_dict(),
                        },
                    )


if __name__ == "__main__":
    main()
