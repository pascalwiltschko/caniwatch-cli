"""Translate transport and response failures into safe errors."""

from typing import Any

import httpx

from caniwatch.application.errors import AppError


def request_json(client: httpx.Client, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError
        return data
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        message = {
            401: "Provider authentication failed. Check the configured API credential.",
            403: "Provider access was denied. Check the account's permissions.",
            429: "Provider quota or rate limit reached. Retry later or check your allowance.",
        }.get(code, f"Provider request failed (HTTP {code}).")
        raise AppError(message) from None
    except httpx.RequestError:
        raise AppError(
            "Provider connection failed. Check connectivity and service availability."
        ) from None
    except (ValueError, TypeError):
        raise AppError("Provider returned an invalid response.") from None
