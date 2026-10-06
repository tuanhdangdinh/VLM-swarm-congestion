"""Transport helpers shared by the HTTP backend adapters.

Each adapter owns its request and response shapes; what is identical across
them -- turning an HTTP error status into a classified exception the shared
retry policy can act on -- lives here, so the four adapters cannot drift on
it the way the conformance review (2026-10-07, F01/F02) found they had.
"""

from __future__ import annotations

from typing import Any

from reasoning.vlm.errors import BackendHTTPError
from reasoning.vlm.retry_policy import parse_retry_after


def http_error(label: str, resp: Any) -> BackendHTTPError:
    """Build the classified error for an HTTP response with status >= 400.

    The message keeps the adapters' historical wording, so artifacts'
    `error_message` reads the same as before the error was classified.

    Args:
        label: Provider label used in the message, e.g. "OpenAI".
        resp: The `requests` response (anything with `status_code`, `text`
            and optionally `headers`).

    Returns:
        A `BackendHTTPError` carrying the status and any `Retry-After`.
    """
    return BackendHTTPError(
        f"{label} returned HTTP {resp.status_code}: {resp.text[:400]}",
        status_code=resp.status_code,
        retry_after_sec=parse_retry_after(getattr(resp, "headers", None)),
    )
