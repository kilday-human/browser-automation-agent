"""LLM client wrapper with token and cost tracking."""

import os
import time
from dataclasses import dataclass, field
from typing import Optional, Literal
from abc import ABC, abstractmethod

# Cost per 1M tokens (adjust as needed)
COSTS = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.8, "output": 4.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
}

# Model tiers for cost optimization
MODEL_TIERS = {
    "anthropic": {
        "fast": "claude-3-5-haiku-20241022",  # Simple tasks
        "smart": "claude-sonnet-4-20250514",   # Complex reasoning
    },
    "openai": {
        "fast": "gpt-4o-mini",
        "smart": "gpt-4o",
    }
}


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float


@dataclass
class LLMStats:
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    calls: list = field(default_factory=list)

    def record(self, response: LLMResponse):
        self.total_calls += 1
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.total_cost += response.cost
        self.total_latency_ms += response.latency_ms
        self.calls.append({
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost": response.cost,
            "latency_ms": response.latency_ms,
        })

    def to_dict(self):
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": round(self.total_cost, 4),
            "total_latency_ms": round(self.total_latency_ms, 2),
        }


class LLMClient(ABC):
    def __init__(self, model: str):
        self.model = model
        self.stats = LLMStats()

    @abstractmethod
    def _call(self, system: str, user: str) -> tuple[str, int, int]:
        """Returns (content, input_tokens, output_tokens)"""
        pass

    def call(self, system: str, user: str) -> LLMResponse:
        start = time.time()
        content, input_tokens, output_tokens = self._call(system, user)
        latency = (time.time() - start) * 1000

        costs = COSTS.get(self.model, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000

        response = LLMResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency,
        )
        self.stats.record(response)
        return response


class AnthropicClient(LLMClient):
    def __init__(self, model: str = "claude-3-5-haiku-20241022"):  # FAST: Default to Haiku
        super().__init__(model)
        from anthropic import Anthropic
        self.client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def _call(self, system: str, user: str) -> tuple[str, int, int]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return (
            response.content[0].text,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

    def call_with_image(self, system: str, user: str, image_base64: str) -> LLMResponse:
        """Call LLM with an image (for visual challenges)."""
        start = time.time()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_base64}},
                    {"type": "text", "text": user},
                ],
            }],
        )
        latency = (time.time() - start) * 1000
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        
        costs = COSTS.get(self.model, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000
        
        resp = LLMResponse(
            content=response.content[0].text,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency,
        )
        self.stats.record(resp)
        return resp


class OpenAIClient(LLMClient):
    def __init__(self, model: str = "gpt-4o"):
        super().__init__(model)
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def _call(self, system: str, user: str) -> tuple[str, int, int]:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (
            response.choices[0].message.content,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )


def get_client(provider: Literal["anthropic", "openai"] = "anthropic", model: Optional[str] = None) -> LLMClient:
    if provider == "anthropic":
        return AnthropicClient(model or "claude-3-5-haiku-20241022")  # FAST: Haiku is 3-5x faster than Sonnet
    elif provider == "openai":
        return OpenAIClient(model or "gpt-4o-mini")  # FAST: mini is 10x faster than gpt-4o
    else:
        raise ValueError(f"Unknown provider: {provider}")
