import logging
import re
import time
from typing import Optional, Tuple

import requests

from core.infrastructure.logging_config import log_event

DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_RETRIES = 2
_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


def post_webhook(
    url: str,
    *,
    json_payload=None,
    data=None,
    files=None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
    backoff_seconds: float = 0.75,
) -> Tuple[bool, Optional[requests.Response], Optional[str]]:
    """Post to a Discord webhook with timeout + retry/backoff.

    Returns:
        (success, response, error_message)
    """
    last_error = None
    response: Optional[requests.Response] = None

    for attempt in range(retries + 1):
        started = time.perf_counter()
        try:
            response = requests.post(
                url,
                json=json_payload,
                data=data,
                files=files,
                timeout=timeout,
            )

            if response.status_code in (200, 204):
                latency_ms = int((time.perf_counter() - started) * 1000)
                log_event(
                    logging.getLogger(__name__),
                    logging.INFO,
                    f"Webhook post succeeded (attempt {attempt + 1})",
                    module="webhook_client",
                    action="webhook_post",
                    outcome="success",
                    latency_ms=latency_ms,
                )
                return True, response, None

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < retries:
                time.sleep(backoff_seconds * (2**attempt))
                continue

            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            latency_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                logging.getLogger(__name__),
                logging.ERROR,
                f"Webhook post failed with HTTP {response.status_code}",
                module="webhook_client",
                action="webhook_post",
                outcome="http_error",
                latency_ms=latency_ms,
            )
            return False, response, f"HTTP {response.status_code}: {payload}"

        except requests.RequestException as exc:
            last_error = str(exc)
            latency_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                logging.getLogger(__name__),
                logging.ERROR,
                f"Webhook post request exception: {last_error}",
                module="webhook_client",
                action="webhook_post",
                outcome="request_exception",
                latency_ms=latency_ms,
            )
            if attempt < retries:
                time.sleep(backoff_seconds * (2**attempt))
                continue

    return False, response, (last_error or "Unknown webhook delivery error")


def append_wait_query(url: str) -> str:
    """Append wait=true to webhook URL preserving existing query string."""
    joiner = "&" if "?" in url else "?"
    return f"{url}{joiner}wait=true"


def log_webhook_result(url: str, success: bool, err: Optional[str] = None) -> None:
    if success:
        logging.info(f"Data sent successfully to {url}.")
    else:
        logging.error(f"Failed to send data to {url}. {err or ''}")


def _extract_http_status(err: Optional[str]) -> Optional[int]:
    if not err:
        return None
    match = re.search(r"HTTP\s+(\d{3})", err)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def classify_webhook_error(err: Optional[str]) -> tuple[str, str]:
    """Classify a webhook error and return (short_reason, user_guidance)."""
    text = (err or "Unknown webhook delivery error").strip()
    lowered = text.lower()
    status = _extract_http_status(text)

    if "timed out" in lowered or "timeout" in lowered:
        return (
            "Request timed out",
            "Discord or your network was slow to respond. Retry, or increase timeout if this keeps happening.",
        )

    if any(
        token in lowered
        for token in (
            "name or service not known",
            "nodename nor servname",
            "failed to establish a new connection",
            "temporary failure in name resolution",
            "connection refused",
            "max retries exceeded",
        )
    ):
        return (
            "Network/DNS connection error",
            "Check internet/DNS connectivity and confirm the webhook hostname resolves correctly.",
        )

    if status == 400:
        return (
            "Discord rejected payload (HTTP 400)",
            "Payload is invalid for Discord. Verify embed/content fields and attachment formatting.",
        )
    if status == 401:
        return (
            "Unauthorized webhook (HTTP 401)",
            "Webhook credentials are invalid. Recreate the webhook URL and update settings.",
        )
    if status == 403:
        return (
            "Forbidden webhook (HTTP 403)",
            "Webhook exists but cannot post to this channel/thread. Check permissions and channel restrictions.",
        )
    if status == 404:
        return (
            "Unknown webhook (HTTP 404)",
            "Webhook URL is invalid or deleted. Replace it in Settings.",
        )
    if status == 429:
        return (
            "Rate limited (HTTP 429)",
            "Too many requests were sent. Wait briefly and try again.",
        )
    if status is not None and 500 <= status <= 599:
        return (
            f"Discord server error (HTTP {status})",
            "Discord had a temporary server-side issue. Retry in a moment.",
        )

    if status is not None:
        return (
            f"HTTP {status} error",
            "Request failed. Verify the webhook URL and try again.",
        )

    return (
        "Unexpected delivery error",
        "Check logs for details, confirm webhook URL format, then retry.",
    )


def format_webhook_failure_line(destination: str, err: Optional[str]) -> str:
    short_reason, guidance = classify_webhook_error(err)
    return f"- {destination}: {short_reason}. {guidance}"