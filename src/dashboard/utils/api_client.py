"""
HTTP client for the Streamlit frontend -> FastAPI backend boundary.

The dashboard deliberately does not open SQLite connections directly once this
module is used by a screen. Local development defaults to the same machine's
FastAPI service; deployment can override the URL with N100_API_BASE_URL.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable

import httpx
import streamlit as st

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"


class APIClientError(RuntimeError):
    """Raised when the dashboard cannot obtain a valid response from FastAPI."""


class _TransientAPIClientError(APIClientError):
    """Internal error used for retryable hosted-backend startup failures."""


def get_api_base_url() -> str:
    """Return the configured FastAPI base URL without a trailing slash."""
    return os.getenv("N100_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")


def _is_local_api(base_url: str) -> bool:
    """Return True when the dashboard is configured for local FastAPI development."""
    return base_url == DEFAULT_API_BASE_URL


def _unreachable_message(base_url: str) -> str:
    """Build a concise user-facing connection message."""
    if _is_local_api(base_url):
        return (
            "FastAPI is not running locally. "
            "Start it with `uvicorn src.api.main:app --port 8000 --reload`."
        )

    return (
        "The hosted backend is waking from inactivity. "
        "Please wait a moment while it starts."
    )


@st.cache_data(ttl=30, show_spinner=False)
def _get(
    base_url: str,
    path: str,
    params: tuple[tuple[str, Any], ...] = (),
) -> dict[str, Any]:
    """GET a JSON endpoint with transient hosted-backend retries."""
    url = f"{base_url}/{path.lstrip('/')}"
    is_local = _is_local_api(base_url)
    total_attempts = 1 if is_local else 4

    for attempt in range(1, total_attempts + 1):
        try:
            response = httpx.get(
                url,
                params=dict(params),
                timeout=10.0,
                follow_redirects=True,
            )
        except httpx.RequestError as exc:
            if attempt < total_attempts and not is_local:
                time.sleep(min(2.0 * attempt, 5.0))
                continue
            raise APIClientError(_unreachable_message(base_url)) from exc

        if response.status_code in {502, 503, 504} and not is_local:
            if attempt < total_attempts:
                time.sleep(min(2.0 * attempt, 5.0))
                continue
            raise APIClientError(_unreachable_message(base_url))

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise APIClientError(
                f"FastAPI returned HTTP {response.status_code}: {detail}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise APIClientError(
                "FastAPI returned a non-JSON response where JSON was expected."
            ) from exc

    raise APIClientError(_unreachable_message(base_url))


def _health_request(
    base_url: str,
    *,
    timeout: float,
) -> dict[str, Any]:
    """Perform one uncached health request for live connection status."""
    url = f"{base_url}/health"
    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
        )
    except httpx.RequestError as exc:
        if _is_local_api(base_url):
            raise APIClientError(_unreachable_message(base_url)) from exc
        raise _TransientAPIClientError(_unreachable_message(base_url)) from exc

    if response.status_code in {502, 503, 504} and not _is_local_api(base_url):
        raise _TransientAPIClientError(_unreachable_message(base_url))

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise APIClientError(
            f"FastAPI returned HTTP {response.status_code}: {detail}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise APIClientError(
            "FastAPI returned a non-JSON health response where JSON was expected."
        ) from exc


def health(
    *,
    max_wait: float = 90.0,
    timeout: float = 5.0,
    retry_delay: float = 2.5,
    on_attempt: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Return backend health, tolerating a hosted Render cold start.

    Local development makes one request and returns the normal Uvicorn guidance
    immediately when FastAPI is not running. The hosted deployment retries
    transient connection failures and 502/503/504 responses until the backend
    responds or the bounded startup window expires.
    """
    base_url = get_api_base_url()
    is_local = _is_local_api(base_url)

    if is_local:
        return _health_request(base_url, timeout=timeout)

    deadline = time.monotonic() + max(1.0, max_wait)
    last_error: APIClientError | None = None

    # The callback receives a conservative attempt budget for UI messaging.
    # The actual loop is bounded by max_wait rather than by a fixed attempt count.
    estimated_attempts = max(1, int(max_wait // max(timeout + retry_delay, 1.0)) + 1)
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        if on_attempt is not None:
            on_attempt(attempt, estimated_attempts)

        remaining = deadline - time.monotonic()
        request_timeout = min(timeout, max(0.1, remaining))

        try:
            return _health_request(base_url, timeout=request_timeout)
        except _TransientAPIClientError as exc:
            last_error = exc
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(retry_delay, remaining))
        except APIClientError:
            raise

    if last_error is not None:
        raise last_error
    raise APIClientError(_unreachable_message(base_url))


def _params(**kwargs: Any) -> tuple[tuple[str, Any], ...]:
    """Convert keyword arguments to a stable, cacheable parameter tuple."""
    return tuple((key, value) for key, value in sorted(kwargs.items()) if value is not None)


def get_companies(
    *, sector: str | None = None, market_cap_category: str | None = None, search: str | None = None
) -> dict[str, Any]:
    """Return companies from the backend."""
    return _get(get_api_base_url(), "companies", _params(sector=sector, market_cap_category=market_cap_category, search=search))


def get_company_profile(ticker: str) -> dict[str, Any]:
    """Return profile, sector, latest KPIs and pros/cons for one company."""
    return _get(get_api_base_url(), f"companies/{ticker}")


def get_company_ratios(ticker: str) -> dict[str, Any]:
    """Return full ratio history for a company."""
    return _get(get_api_base_url(), f"companies/{ticker}/ratios")


def get_company_pl(ticker: str) -> dict[str, Any]:
    """Return P&L history for a company."""
    return _get(get_api_base_url(), f"companies/{ticker}/pl")


def get_company_cashflow(ticker: str) -> dict[str, Any]:
    """Return cash-flow history for a company."""
    return _get(get_api_base_url(), f"companies/{ticker}/cashflow")


def get_company_documents(ticker: str) -> dict[str, Any]:
    """Return annual-report links for a company."""
    return _get(get_api_base_url(), f"companies/{ticker}/documents")


def get_screener(**filters: float | str | None) -> dict[str, Any]:
    """Run the backend screener with any supported threshold filters."""
    return _get(get_api_base_url(), "screener", _params(**filters))


def get_home(year: int) -> dict[str, Any]:
    """Return the dashboard home read model for the requested calendar year."""
    return _get(get_api_base_url(), "dashboard/home", _params(year=year))


def get_peer_group(group_name: str) -> dict[str, Any]:
    """Return peer members, names, latest KPIs and percentile metrics."""
    return _get(get_api_base_url(), f"peers/{group_name}")


def get_peer_comparison(ticker: str) -> dict[str, Any]:
    """Return one company's peer comparison read model."""
    return _get(get_api_base_url(), f"companies/{ticker}/peers/compare")


def get_peer_group_names() -> list[str]:
    """Return peer-group names using the backend's peer listing endpoint."""
    # The API contract exposes group names through the response set rather than
    # a dedicated metadata endpoint, so use a lightweight endpoint added for the UI.
    return _get(get_api_base_url(), "peers")["peer_groups"]


def get_sectors() -> dict[str, Any]:
    """Return all sectors and summary statistics."""
    return _get(get_api_base_url(), "sectors")


def get_sector_companies(sector_name: str) -> dict[str, Any]:
    """Return the latest analysis dataset for one sector."""
    return _get(get_api_base_url(), f"sectors/{sector_name}/companies")


def get_capital_allocation() -> dict[str, Any]:
    """Return the capital-allocation read model for all companies."""
    return _get(get_api_base_url(), "dashboard/capital-allocation")