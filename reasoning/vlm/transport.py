"""Transport helpers shared by the HTTP backend adapters.

Each adapter owns its request and response shapes; what is identical across
them -- turning an HTTP error status into a classified exception the shared
retry policy can act on, redacting the key from error text, reading the
provider's request id -- lives here, so the four adapters cannot drift on it
the way the conformance review (2026-10-07, F01/F02/F15/F18) found they had.
The full adapter dedup (F20) is deferred to v3.
"""

from __future__ import annotations

from typing import Any

from reasoning.vlm.errors import BackendHTTPError
from reasoning.vlm.retry_policy import parse_retry_after

_REDACTED = "***REDACTED***"
_ERROR_TEXT_LIMIT = 400


def redact_secret(text: str, secret: str | None) -> str:
    """Replace every occurrence of `secret` in `text` with a redaction marker.

    The same contract as `scripts/probe_gemini_er2.py:redact_secret` (F15).

    Args:
        text: Text that may contain the secret (e.g. an HTTP error body).
        secret: The literal secret value to scrub, or None/empty to skip.

    Returns:
        `text` with every occurrence of `secret` replaced by
        `***REDACTED***`; unchanged if `secret` is falsy.
    """
    if not secret:
        return text
    return text.replace(secret, _REDACTED)


def safe_error_text(text: str, secret: str | None) -> str:
    """Redact, then truncate, text bound for an artifact's `error_message`.

    Redaction runs first so a key straddling the truncation point cannot
    leave a fragment behind.

    Args:
        text: Raw error text (an HTTP body or an exception message).
        secret: The adapter's key, or None for a keyless backend.

    Returns:
        At most 400 characters with the key scrubbed.
    """
    return redact_secret(text, secret)[:_ERROR_TEXT_LIMIT]


def header_value(resp: Any, name: str) -> str | None:
    """Read one response header case-insensitively.

    Args:
        resp: A `requests` response or a test double (headers optional).
        name: Header name.

    Returns:
        The header's value, or None when absent.
    """
    headers = getattr(resp, "headers", None)
    if not headers:
        return None
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted and value:
            return str(value)
    return None


def json_body(resp: Any) -> dict | None:
    """Return the response body as a dict, or None if it is not a JSON object."""
    try:
        data = resp.json()
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def provider_error_code(body: dict | None) -> str | None:
    """Read the provider's error code from an error body.

    Every hosted provider wraps errors as `{"error": {"code": ..., ...}}`
    (OpenAI, DeepSeek, Zhipu -- whose code may be a string or an integer --
    and Gemini); Anthropic uses `{"type": "error", "error": {"type": ...}}`.

    Args:
        body: The parsed error body, if any.

    Returns:
        The code (or, failing that, the error type) as a string, or None.
    """
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if not isinstance(error, dict):
        return None
    for key in ("code", "type"):
        value = error.get(key)
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value):
            return str(value)
    return None


def provider_request_id(resp: Any, body: dict | None, header: str | None = None) -> str | None:
    """Return the provider's id for a call (F18).

    Args:
        resp: The response (for the header).
        body: The parsed body, if any.
        header: The provider's request-id header name (`x-request-id` for
            OpenAI, `request-id` for Anthropic), if it documents one.

    Returns:
        The header value when present, else the body's `request_id` (Zhipu,
        Anthropic error bodies), else the body's `id` (completion or
        interaction id), else None.
    """
    if header is not None:
        value = header_value(resp, header)
        if value:
            return value
    if isinstance(body, dict):
        for key in ("request_id", "id"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def http_error(
    label: str,
    resp: Any,
    secret: str | None = None,
    request_id_header: str | None = None,
) -> BackendHTTPError:
    """Build the classified error for an HTTP response with status >= 400.

    The message keeps the adapters' historical wording, so artifacts'
    `error_message` reads the same as before the error was classified; the
    body is redacted before it is truncated (F15).

    Args:
        label: Provider label used in the message, e.g. "OpenAI".
        resp: The `requests` response (anything with `status_code`, `text`
            and optionally `headers` / `json()`).
        secret: The adapter's API key, scrubbed from the body text.
        request_id_header: The provider's request-id header name, if any.

    Returns:
        A `BackendHTTPError` carrying the status, any `Retry-After`, the
        provider's error code and its request id.
    """
    body = json_body(resp)
    return BackendHTTPError(
        f"{label} returned HTTP {resp.status_code}: {safe_error_text(resp.text, secret)}",
        status_code=resp.status_code,
        retry_after_sec=parse_retry_after(getattr(resp, "headers", None)),
        provider_code=provider_error_code(body),
        request_id=provider_request_id(resp, body, request_id_header),
    )
