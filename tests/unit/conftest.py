"""Unit-test fixtures shared across the suite (transport hotfix, 2026-10-07)."""
import pytest


@pytest.fixture(autouse=True)
def _no_real_retry_backoff(monkeypatch):
    """Make the shared M2 retry policy's default sleep a no-op in unit tests.

    The policy (transport hotfix F02) waits seconds between retryable
    attempts; tests that exercise retries would otherwise sleep for real.
    Tests that assert on the waits inject their own `RetryPolicy(sleep=...)`.
    """
    monkeypatch.setattr("reasoning.vlm.retry_policy._sleep_impl", lambda seconds: None)
