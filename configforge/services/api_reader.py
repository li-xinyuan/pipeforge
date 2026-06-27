import logging
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from configforge.utils.security import resolve_url_to_ip

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_PAGES = 10
DEFAULT_PAGE_SIZE = 100


def read_api_info(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    data_path: str = "",
    pagination: str = "none",
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_sample_rows: int = 10,
) -> dict:
    """Read data from a REST API, return columns and sample_rows (same interface as read_excel_info).

    Args:
        url: API endpoint URL
        method: HTTP method (GET or POST)
        headers: Custom HTTP headers
        params: Query parameters
        body: Request body (for POST)
        data_path: JSON path to data array (e.g. "data.items")
        pagination: Pagination type ("none", "offset", "cursor")
        page_size: Number of items per page
        max_pages: Maximum number of pages to fetch
        max_sample_rows: Max number of sample rows to return
    """
    headers = headers or {}
    params = dict(params or {})
    resolved_ip: str | None = None
    try:
        resolved_ip, _ = resolve_url_to_ip(url)
    except ValueError:
        # DNS resolution failed (e.g. test env), fall back to direct URL without IP locking
        logger.warning("DNS resolution failed for %s, falling back to direct connection", url)
    all_items: list[dict] = []

    if pagination == "none":
        items = _fetch_page(url, method, headers, params, body, data_path, resolved_ip)
        all_items = items[:50000]
    elif pagination == "offset":
        for page in range(max_pages):
            params["offset"] = str(page * page_size)
            params["limit"] = str(page_size)
            items = _fetch_page(url, method, headers, params, body, data_path, resolved_ip)
            all_items.extend(items)
            if len(items) < page_size:
                break
            if len(all_items) >= 50000:
                break
    elif pagination == "cursor":
        cursor = ""
        for _ in range(max_pages):
            if cursor:
                params["cursor"] = cursor
            items, next_cursor = _fetch_page_cursor(url, method, headers, params, body, data_path, resolved_ip)
            all_items.extend(items)
            if not next_cursor:
                break
            cursor = next_cursor
            if len(all_items) >= 50000:
                break

    if not all_items:
        return {"sheets": [], "columns": [], "sample_rows": []}

    # Collect all keys
    all_keys: list[str] = []
    for item in all_items:
        if isinstance(item, dict):
            for key in item:
                if key not in all_keys:
                    all_keys.append(key)

    columns = all_keys
    sample_rows = []
    for item in all_items[:max_sample_rows]:
        if isinstance(item, dict):
            sample_rows.append([str(item.get(col, "")) for col in columns])

    return {
        "sheets": [],
        "columns": columns,
        "sample_rows": sample_rows,
    }


def _build_ip_locked_url(url: str, resolved_ip: str) -> str:
    """Replace hostname in URL with resolved IP, preserving original Host header."""
    parsed = urlparse(url)
    # Replace hostname with resolved IP, keep port if present
    if parsed.port:
        netloc = f"{resolved_ip}:{parsed.port}"
    else:
        netloc = resolved_ip
    return urlunparse(parsed._replace(netloc=netloc))


def _fetch_page(
    url: str,
    method: str,
    headers: dict[str, str],
    params: dict[str, str],
    body: dict[str, Any] | None,
    data_path: str,
    resolved_ip: str | None = None,
) -> list[dict]:
    """Fetch a single page from the API.

    If resolved_ip is provided, connects to that IP directly to prevent DNS rebinding.
    The original hostname is sent in the Host header for proper virtual hosting.
    """
    actual_url = url
    request_headers = dict(headers)
    if resolved_ip:
        parsed = urlparse(url)
        if parsed.hostname and parsed.hostname != resolved_ip:
            # Set Host header to original hostname for virtual hosting
            if parsed.port:
                request_headers.setdefault("Host", f"{parsed.hostname}:{parsed.port}")
            else:
                request_headers.setdefault("Host", parsed.hostname)
            actual_url = _build_ip_locked_url(url, resolved_ip)
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            if method.upper() == "POST":
                resp = client.post(actual_url, headers=request_headers, params=params, json=body)
            else:
                resp = client.get(actual_url, headers=request_headers, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("API request failed: %s", e)
        raise ValueError(f"API request failed: {e}") from e

    data = resp.json()
    return _extract_data(data, data_path)


def _fetch_page_cursor(
    url: str,
    method: str,
    headers: dict[str, str],
    params: dict[str, str],
    body: dict[str, Any] | None,
    data_path: str,
    resolved_ip: str | None = None,
) -> tuple[list[dict], str]:
    """Fetch a single page and return items + next cursor.

    If resolved_ip is provided, connects to that IP directly to prevent DNS rebinding.
    """
    actual_url = url
    request_headers = dict(headers)
    if resolved_ip:
        parsed = urlparse(url)
        if parsed.hostname and parsed.hostname != resolved_ip:
            if parsed.port:
                request_headers.setdefault("Host", f"{parsed.hostname}:{parsed.port}")
            else:
                request_headers.setdefault("Host", parsed.hostname)
            actual_url = _build_ip_locked_url(url, resolved_ip)
    try:
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            if method.upper() == "POST":
                resp = client.post(actual_url, headers=request_headers, params=params, json=body)
            else:
                resp = client.get(actual_url, headers=request_headers, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("API request failed: %s", e)
        raise ValueError(f"API request failed: {e}") from e

    data = resp.json()
    items = _extract_data(data, data_path)
    next_cursor = data.get("next_cursor", data.get("nextCursor", ""))
    if isinstance(next_cursor, dict):
        next_cursor = str(next_cursor)
    return items, next_cursor


def _extract_data(data: Any, data_path: str) -> list[dict]:
    """Extract data array from response using dot-notation path."""
    if data_path:
        for key in data_path.split("."):
            if isinstance(data, dict):
                data = data.get(key, [])
            else:
                data = []
                break

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Single object -> wrap in array
        return [data]
    return []
