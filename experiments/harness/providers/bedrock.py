from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError

from providers.base import BaseLLMProvider, ProviderUsage
from runners.patch_runner import PatchToolExecutor, ToolExecutionResult


ANTHROPIC_VERSION = "bedrock-2023-05-31"


@dataclass
class BedrockToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class BedrockProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        model_id: str,
        profile_name: str = "codeboost",
        region_name: str = "us-east-1",
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> None:
        super().__init__(model_id=model_id, max_tokens=max_tokens, temperature=temperature)
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        self.client = session.client("bedrock-runtime")
        self.profile_name = profile_name
        self.region_name = region_name
        self.invoke_target = model_id

    def complete(self, prompt: str) -> str:
        payload = self._invoke_messages(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        )
        return self._extract_text(payload)

    def solve(self, prompt: str, tools: PatchToolExecutor) -> str:
        tool_schemas = self._tool_schemas()
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]
        final_text = ""

        for _ in range(30):
            payload = self._invoke_messages(messages=messages, tools=tool_schemas)
            content = payload.get("content", [])
            stop_reason = payload.get("stop_reason", "")
            messages.append({"role": "assistant", "content": content})

            tool_uses = [block for block in content if block.get("type") == "tool_use"]
            text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
            if text_blocks:
                final_text = "\n".join(part for part in text_blocks if part).strip() or final_text

            if stop_reason != "tool_use" or not tool_uses:
                return final_text

            tool_results = []
            for tool_use in tool_uses:
                result = self._execute_tool(
                    executor=tools,
                    tool_name=tool_use["name"],
                    tool_input=tool_use.get("input", {}),
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use["id"],
                        "content": result,
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        raise RuntimeError("Bedrock tool loop exceeded maximum iterations.")

    def _invoke_messages(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": messages,
        }
        if tools:
            body["tools"] = tools

        try:
            response = self.client.invoke_model(
                modelId=self.invoke_target,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
        except ClientError as exc:
            message = str(exc)
            if "inference profile" not in message.lower():
                raise

            fallback_target = self._inference_profile_target()
            if fallback_target == self.invoke_target:
                raise

            self.invoke_target = fallback_target
            response = self.client.invoke_model(
                modelId=self.invoke_target,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
        payload = json.loads(response["body"].read())
        usage = payload.get("usage", {})
        self.last_usage = ProviderUsage(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            stop_reason=payload.get("stop_reason", ""),
        )
        return payload

    def _inference_profile_target(self) -> str:
        if self.model_id.startswith(("us.", "global.", "arn:aws:bedrock:")):
            return self.model_id
        return f"us.{self.model_id}"

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        parts = [
            block.get("text", "")
            for block in payload.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(part for part in parts if part).strip()

    @staticmethod
    def _tool_schemas() -> list[dict[str, Any]]:
        specs = [
            BedrockToolSpec(
                name="list_files",
                description="List files available in the current workspace.",
                input_schema={"type": "object", "properties": {}, "required": []},
            ),
            BedrockToolSpec(
                name="read_file",
                description="Read a UTF-8 text file from the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {"relative_path": {"type": "string"}},
                    "required": ["relative_path"],
                },
            ),
            BedrockToolSpec(
                name="edit_file",
                description="Overwrite a UTF-8 text file in the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "relative_path": {"type": "string"},
                        "new_content": {"type": "string"},
                    },
                    "required": ["relative_path", "new_content"],
                },
            ),
            BedrockToolSpec(
                name="run_tests",
                description="Run the standardized validation command for the workspace.",
                input_schema={"type": "object", "properties": {}, "required": []},
            ),
            BedrockToolSpec(
                name="run_arch_lint",
                description="Run the architecture linter and return a JSON report.",
                input_schema={"type": "object", "properties": {}, "required": []},
            ),
        ]
        return [spec.to_dict() for spec in specs]

    @staticmethod
    def _serialize_tool_result(result: Any) -> str:
        if isinstance(result, ToolExecutionResult):
            return json.dumps(result.to_dict(), indent=2)
        if isinstance(result, (dict, list)):
            return json.dumps(result, indent=2)
        if result is None:
            return json.dumps({"ok": True})
        return str(result)

    def _execute_tool(
        self,
        *,
        executor: PatchToolExecutor,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> str:
        if tool_name == "list_files":
            return self._serialize_tool_result(executor.list_files())
        if tool_name == "read_file":
            return self._serialize_tool_result(executor.read_file(tool_input["relative_path"]))
        if tool_name == "edit_file":
            executor.edit_file(tool_input["relative_path"], tool_input["new_content"])
            return self._serialize_tool_result({"ok": True, "path": tool_input["relative_path"]})
        if tool_name == "run_tests":
            return self._serialize_tool_result(executor.run_tests())
        if tool_name == "run_arch_lint":
            return self._serialize_tool_result(executor.run_arch_lint())
        raise ValueError(f"Unsupported tool requested by model: {tool_name}")
