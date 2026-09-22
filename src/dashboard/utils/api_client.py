"""
HTTP client for the Streamlit frontend -> FastAPI backend boundary.

The dashboard deliberately does not open SQLite connections directly once this
module is used by a screen. Local development defaults to the same machine's
FastAPI service; deployment can override the URL with N100_API_BASE_URL.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"


class APIClientError(RuntimeError):
    """Raised when the dashboard cannot obtain a valid response from FastAPI."""


def get_api_base_url() -> str:
    """Return the configured FastAPI base URL without a trailing slash."""
    return os.getenv("N100_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")


@st.cache_data(ttl=30, show_spinner=False)
def _get(base_url: str, path: str, params: tuple[tuple[str, Any], ...] = ()) -> dict[str, Any]:
    """GET a JSON endpoint and normalize transport/API failures for Streamlit."""
    url = f"{base_url}/{path.lstrip('/')}"
    try:
        response = httpx.get(url, params=dict(params), timeout=10.0)
    except httpx.RequestError as exc:
        raise APIClientError(
            f"FastAPI is not reachable at {base_url}. "
            "Start the API with `uvicorn src.api.main:app --port 8000 --reload`."
        ) from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise APIClientError(f"FastAPI returned HTTP {response.status_code}: {detail}")

    try:
        return response.json()
    except ValueError as exc:
        raise APIClientError("FastAPI returned a non-JSON response where JSON was expected.") from exc


def _params(**kwargs: Any) -> tuple[tuple[str, Any], ...]:
    """Convert keyword arguments to a stable, cacheable parameter tuple."""
    return tuple((key, value) for key, value in sorted(kwargs.items()) if value is not None)


def health() -> dict[str, Any]:
    """Return backend health information."""
    return _get(get_api_base_url(), "health")


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