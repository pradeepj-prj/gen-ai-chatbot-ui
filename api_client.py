"""HTTP client for the SAP AI Documentation Assistant API.

No Streamlit imports — this module is pure HTTP logic so it can be
tested independently.
"""

import requests

from config import (
    ASK_ENDPOINT,
    HEALTH_ENDPOINT,
    REQUEST_TIMEOUT,
    SERVICES_ENDPOINT,
)


class APIError(Exception):
    """Raised when an API call fails (connection, timeout, or HTTP error)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def check_health() -> dict:
    """GET /health — returns {"status": "healthy", "service": ..., "version": ...}."""
    try:
        resp = requests.get(HEALTH_ENDPOINT, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        raise APIError("Cannot connect to the API. Is the backend running?")
    except requests.Timeout:
        raise APIError("Health check timed out.")
    except requests.HTTPError as exc:
        raise APIError(
            f"Health check failed: {exc.response.status_code}",
            status_code=exc.response.status_code,
        )


def fetch_services() -> list[dict]:
    """GET /api/v1/kb/services — returns list of service dicts with key, display_name, description, doc_count."""
    try:
        resp = requests.get(SERVICES_ENDPOINT, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        raise APIError("Cannot connect to the API. Is the backend running?")
    except requests.Timeout:
        raise APIError("Service list request timed out.")
    except requests.HTTPError as exc:
        raise APIError(
            f"Failed to fetch services: {exc.response.status_code}",
            status_code=exc.response.status_code,
        )


def ask_question(question: str, show_pipeline: bool = False) -> dict:
    """POST /api/v1/ask — returns the full AskResponse dict."""
    payload = {
        "question": question,
        "show_pipeline": show_pipeline,
    }
    try:
        resp = requests.post(
            ASK_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        raise APIError("Cannot connect to the API. Is the backend running?")
    except requests.Timeout:
        raise APIError(
            "The request timed out. The API may be under heavy load — please try again."
        )
    except requests.HTTPError as exc:
        raise APIError(
            f"API error: {exc.response.status_code}",
            status_code=exc.response.status_code,
        )
