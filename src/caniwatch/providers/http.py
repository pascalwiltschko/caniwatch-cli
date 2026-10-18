"""Translate transport and response failures into safe errors."""

import logging
from typing import Any, Literal

import httpx

from caniwatch.application.errors import AppError

logger = logging.getLogger(__name__)


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    provider: Literal["TMDB", "Tavily", "Ollama"],
    operation: Literal["search", "details", "models", "assessment", "compatibility"],
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError
        return data
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        reason = "http_error"
        logger.warning(
            "provider=%s operation=%s reason=%s http_status=%d", provider, operation, reason, code
        )
        message = {
            401: "Provider authentication failed. Check the configured API credential.",
            403: "Provider access was denied. Check the account's permissions.",
            429: "Provider quota or rate limit reached. Retry later or check your allowance.",
            404: "Endpoint or model not found. Check the service and installed model.",
            501: (
                "Requested capability is unavailable. For Ollama structured output, use a "
                "GGUF model such as gemma4:e4b-it-q4_K_M, set CANIWATCH_MODEL, and run --doctor."
                if provider == "Ollama"
                else "Requested capability is unavailable. Update the service."
            ),
        }.get(code, f"Provider request failed (HTTP {code}).")
        raise AppError(
            f"{provider} {operation} failed (HTTP {code}). {message}",
        ) from None
    except httpx.RequestError as exc:
        reason = "timeout" if isinstance(exc, httpx.TimeoutException) else "connection_error"
        logger.warning("provider=%s operation=%s reason=%s", provider, operation, reason)
        description = "timed out" if reason == "timeout" else "connection failed"
        raise AppError(
            f"{provider} {operation} {description}. Check connectivity and service availability.",
        ) from None
    except (ValueError, TypeError):
        logger.warning("provider=%s operation=%s reason=invalid_response", provider, operation)
        raise AppError(f"{provider} {operation} returned an invalid response.") from None
