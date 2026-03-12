from __future__ import annotations

import json
from typing import Any

import requests


DEFAULT_TIMEOUT = 30


def get_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def post_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    merged_headers = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        merged_headers.update(headers)
    response = requests.post(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=merged_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    if response.content:
        return response.json()
    return {}
