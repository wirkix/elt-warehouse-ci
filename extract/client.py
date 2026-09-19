"""Thin client for the balldontlie NBA API (https://balldontlie.io).

Free tier is 5 requests/minute and cursor-paginated (`meta.next_cursor`,
not offset/limit) -- this client throttles to that rate and follows the
cursor automatically. Raise BALLDONTLIE_RATE_LIMIT_PER_MIN only if the
account is upgraded to a paid plan.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import requests

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

BASE_URL = "https://api.balldontlie.io/v1"
RATE_LIMIT_PER_MIN = 5
SECONDS_BETWEEN_REQUESTS = 60 / RATE_LIMIT_PER_MIN
MAX_RETRIES = 5


class BalldontlieError(RuntimeError):
    pass


class BalldontlieClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.environ["BALLDONTLIE_API_KEY"]
        self.session = session or requests.Session()
        self._last_request_at: float | None = None

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = SECONDS_BETWEEN_REQUESTS - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _get(self, path: str, params: dict) -> dict:
        url = f"{BASE_URL}{path}"
        headers = {"Authorization": self.api_key}
        for attempt in range(MAX_RETRIES):
            self._throttle()
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            self._last_request_at = time.monotonic()
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", SECONDS_BETWEEN_REQUESTS))
                time.sleep(retry_after)
                continue
            if response.status_code >= 500:
                time.sleep(SECONDS_BETWEEN_REQUESTS * (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        raise BalldontlieError(f"Exhausted retries against {url} with params={params}")

    def paginate(self, path: str, params: dict | None = None, per_page: int = 100) -> Iterator[dict]:
        """Yield every raw item from a cursor-paginated endpoint."""
        params = dict(params or {})
        params["per_page"] = per_page
        cursor: int | None = None
        while True:
            request_params = dict(params)
            if cursor is not None:
                request_params["cursor"] = cursor
            payload = self._get(path, request_params)
            yield from payload["data"]
            cursor = payload.get("meta", {}).get("next_cursor")
            if not cursor:
                return

    def teams(self) -> Iterator[dict]:
        return self.paginate("/teams")

    def players(self) -> Iterator[dict]:
        return self.paginate("/players")

    def games(self, seasons: list[int]) -> Iterator[dict]:
        return self.paginate("/games", {"seasons[]": seasons})
