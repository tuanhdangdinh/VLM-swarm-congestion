"""The one retry policy every M2 call (stage 1 and stage 2, all arms) runs under.

Conformance-review ruling F02 (2026-10-07, prereg-v2 design spec): HTTP 429
and 5xx are retried with exponential backoff, honouring `Retry-After` when the
provider sends it; every other 4xx is deterministic and ends the call after
the attempt that received it; attempt budgets are unchanged. Provider guidance
(fetched 2026-10-07): OpenAI rate-limits guide "follow Retry-After when the
header is present ... fall back to exponential backoff with jitter"; Anthropic
errors page, 500 "Retry the request with exponential backoff"; Gemini
api-errors, 429/503 "Wait and retry with exponential backoff".

Parameters (module constants, recorded in
`docs/reports/2026-10-07-conformance-fixes.md`):

- exponential wait before retry `k` (k = 1-based index of the failed
  attempt): ceiling `min(BACKOFF_CAP_SEC, BACKOFF_BASE_SEC * 2**(k-1))`,
  equal jitter -- uniform in `[ceiling/2, ceiling]` -- so a burst of
  concurrent callers spreads out but never retries near-immediately;
- `Retry-After` replaces the exponential wait, clamped to
  `RETRY_AFTER_CAP_SEC` so one header cannot stall the loop indefinitely;
- the waits of one call sum to at most `MAX_TOTAL_BACKOFF_SEC`; once that is
  spent, remaining retries go out without waiting (the budget still bounds
  them);
- no wait follows the final attempt, a timeout (the call already spent
  `timeout_sec`), or an adapter exception that is not a transport failure.
"""

from __future__ import annotations

import email.utils
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from reasoning.vlm.errors import BackendHTTPError, BackendTimeoutError

BACKOFF_BASE_SEC = 2.0
BACKOFF_CAP_SEC = 30.0
RETRY_AFTER_CAP_SEC = 60.0
MAX_TOTAL_BACKOFF_SEC = 90.0

RetryDecision = Literal["backoff", "immediate", "stop"]


def _sleep_impl(seconds: float) -> None:
    # Looked up at call time, so a test suite can replace the real sleep.
    time.sleep(seconds)


def classify_failure(exc: BaseException) -> RetryDecision:
    """Decide how a failed backend call is retried.

    Args:
        exc: The exception the attempt ended with.

    Returns:
        "backoff" for HTTP 429/5xx and transport failures (connection
        errors, bodies closed mid-stream, malformed bodies); "stop" for any
        other HTTP 4xx; "immediate" for a timeout or any other exception.
    """
    if isinstance(exc, BackendHTTPError):
        return "backoff" if exc.retryable else "stop"
    if isinstance(exc, BackendTimeoutError):
        return "immediate"
    if isinstance(exc, ConnectionError):
        return "backoff"
    return "immediate"


def parse_retry_after(headers: Mapping[str, str] | None, now: float | None = None) -> float | None:
    """Read a `Retry-After` header as seconds.

    Args:
        headers: Response headers (any mapping; matched case-insensitively).
        now: Current epoch time for an HTTP-date value; defaults to now.

    Returns:
        Non-negative seconds, or None when the header is absent or invalid.
    """
    if not headers:
        return None
    value = next(
        (str(v) for k, v in headers.items() if str(k).lower() == "retry-after"), None
    )
    if value is None or not value.strip():
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        try:
            when = email.utils.parsedate_to_datetime(value.strip())
        except (TypeError, ValueError):
            return None
        seconds = when.timestamp() - (time.time() if now is None else now)
    if seconds != seconds:  # NaN
        return None
    return max(seconds, 0.0)


@dataclass(frozen=True)
class RetryPolicy:
    """Backoff parameters plus the injectable clock and random source.

    Attributes:
        base_sec: First exponential ceiling.
        cap_sec: Largest exponential ceiling.
        retry_after_cap_sec: Largest honoured `Retry-After`.
        max_total_sec: Largest total wait for one call.
        sleep: Called with each wait; None uses the real sleep.
        rng: Jitter source; None uses the `random` module.
    """

    base_sec: float = BACKOFF_BASE_SEC
    cap_sec: float = BACKOFF_CAP_SEC
    retry_after_cap_sec: float = RETRY_AFTER_CAP_SEC
    max_total_sec: float = MAX_TOTAL_BACKOFF_SEC
    sleep: Callable[[float], None] | None = None
    rng: random.Random | None = None

    def delay(self, failed_attempt: int, retry_after_sec: float | None) -> float:
        """Return the wait before retrying after attempt `failed_attempt`.

        Args:
            failed_attempt: 1-based index of the attempt that failed.
            retry_after_sec: The provider's `Retry-After`, if any.

        Returns:
            Seconds to wait (before the per-call total cap).
        """
        if retry_after_sec is not None:
            return min(max(retry_after_sec, 0.0), self.retry_after_cap_sec)
        ceiling = min(self.cap_sec, self.base_sec * 2 ** max(failed_attempt - 1, 0))
        rng = self.rng if self.rng is not None else random
        return ceiling / 2 + rng.uniform(0.0, ceiling / 2)

    def wait_before_retry(
        self, exc: BaseException, failed_attempt: int, waited_sec: float
    ) -> float:
        """Sleep before the next attempt when `exc` calls for backoff.

        Args:
            exc: The exception the attempt ended with.
            failed_attempt: 1-based index of that attempt.
            waited_sec: Total already waited during this call.

        Returns:
            Seconds actually slept (0.0 when no backoff applies).
        """
        if classify_failure(exc) != "backoff":
            return 0.0
        retry_after = exc.retry_after_sec if isinstance(exc, BackendHTTPError) else None
        remaining = max(self.max_total_sec - waited_sec, 0.0)
        wait = min(self.delay(failed_attempt, retry_after), remaining)
        if wait <= 0.0:
            return 0.0
        (self.sleep if self.sleep is not None else _sleep_impl)(wait)
        return wait


DEFAULT_RETRY_POLICY = RetryPolicy()
