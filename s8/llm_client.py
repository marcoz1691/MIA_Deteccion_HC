"""Cliente LLM con cache JSON, medición de latencia y modo mock para reproducibilidad."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Wrapper OpenAI-compatible con cache en disco."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0,
        max_tokens: int = 10,
        cache_dir: Path | str = "salidas_s8/cache",
        mock: bool = False,
        cost_input_per_1m: float = 0.15,
        cost_output_per_1m: float = 0.60,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.mock = mock
        self.cost_input_per_1m = cost_input_per_1m
        self.cost_output_per_1m = cost_output_per_1m
        self.stats = {"calls": 0, "cache_hits": 0, "total_latency_ms": 0.0,
                      "input_tokens": 0, "output_tokens": 0}

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("MISTRAL_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not mock and api_key:
            from openai import OpenAI
            kwargs = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = OpenAI(**kwargs)
        else:
            self._client = None
            if not mock:
                self.mock = True  # sin API key → mock automático

    def _cache_key(self, prompt: str, brazo: str) -> str:
        h = hashlib.sha256(f"{brazo}|{self.model}|{prompt}".encode()).hexdigest()
        return h

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def complete(self, prompt: str, brazo: str = "llm") -> dict:
        """Retorna {text, latency_ms, cached, input_tokens, output_tokens, cost_usd}."""
        key = self._cache_key(prompt, brazo)
        cache_file = self._cache_path(key)
        if cache_file.exists():
            self.stats["cache_hits"] += 1
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            data["cached"] = True
            return data

        t0 = time.perf_counter()
        if self.mock or self._client is None:
            text = self._mock_response(prompt)
            input_tokens = len(prompt.split()) * 2
            output_tokens = 2
        else:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            text = resp.choices[0].message.content or "NO"
            usage = resp.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

        latency_ms = (time.perf_counter() - t0) * 1000
        cost = (
            input_tokens * self.cost_input_per_1m / 1_000_000
            + output_tokens * self.cost_output_per_1m / 1_000_000
        )
        self.stats["calls"] += 1
        self.stats["total_latency_ms"] += latency_ms
        self.stats["input_tokens"] += input_tokens
        self.stats["output_tokens"] += output_tokens

        data = {
            "text": text,
            "latency_ms": round(latency_ms, 2),
            "cached": False,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "model": self.model,
            "brazo": brazo,
        }
        cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    @staticmethod
    def _mock_response(prompt: str) -> str:
        """Heurística determinista para demo sin API (basada en keywords clínicos)."""
        p = prompt.lower()
        triggers = [
            "contradict", "inconsistent", "incorrect dose", "allergy",
            "despite", "however", "but patient", "sin embargo", "contradic",
            "alergia", "dosis incorrecta",
        ]
        if any(t in p for t in triggers):
            return "YES"
        return "NO"

    def summary(self) -> dict:
        calls = self.stats["calls"]
        avg_lat = self.stats["total_latency_ms"] / calls if calls else 0
        total_cost = (
            self.stats["input_tokens"] * self.cost_input_per_1m / 1_000_000
            + self.stats["output_tokens"] * self.cost_output_per_1m / 1_000_000
        )
        return {
            "api_calls": calls,
            "cache_hits": self.stats["cache_hits"],
            "avg_latency_ms": round(avg_lat, 2),
            "total_input_tokens": self.stats["input_tokens"],
            "total_output_tokens": self.stats["output_tokens"],
            "estimated_cost_usd": round(total_cost, 4),
            "mock_mode": self.mock,
        }
