"""La espera ante 429 debe respetar el 'try again in' de OpenAI."""
from __future__ import annotations

from s7.llm_client import delay_for_api_error


def test_delay_429_honors_try_again_ms():
    exc = RuntimeError(
        "Rate limit reached for gpt-4o-mini ... Please try again in 536ms."
    )
    delay = delay_for_api_error(exc, attempt=0, base=0.5)
    assert delay >= 0.536


def test_delay_429_honors_try_again_seconds():
    exc = RuntimeError("rate_limit_exceeded Please try again in 1.011s.")
    delay = delay_for_api_error(exc, attempt=0, base=0.5)
    assert delay >= 1.011


def test_delay_connection_error_keeps_exponential_backoff():
    delay = delay_for_api_error(ConnectionError("down"), attempt=1, base=0.01)
    assert abs(delay - 0.02) < 1e-9
