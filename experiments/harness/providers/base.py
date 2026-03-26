from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

from runners.patch_runner import PatchToolExecutor


@dataclass
class ProviderUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class BaseLLMProvider(ABC):
    def __init__(self, *, model_id: str, max_tokens: int = 2048, temperature: float = 0.0) -> None:
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.last_usage = ProviderUsage()

    @abstractmethod
    def complete(self, prompt: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def solve(self, prompt: str, tools: PatchToolExecutor) -> str:
        raise NotImplementedError
