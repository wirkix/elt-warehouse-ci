from unittest.mock import patch

import responses

from extract.client import BASE_URL, BalldontlieClient


def make_client() -> BalldontlieClient:
    return BalldontlieClient(api_key="test-key")


@responses.activate
@patch("extract.client.time.sleep")
def test_paginate_follows_cursor_across_pages(mock_sleep):
    responses.add(
        responses.GET,
        f"{BASE_URL}/teams",
        json={"data": [{"id": 1}, {"id": 2}], "meta": {"next_cursor": 2, "per_page": 100}},
        match=[responses.matchers.query_param_matcher({"per_page": "100"})],
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/teams",
        json={"data": [{"id": 3}], "meta": {"next_cursor": None, "per_page": 100}},
        match=[responses.matchers.query_param_matcher({"per_page": "100", "cursor": "2"})],
    )

    items = list(make_client().paginate("/teams"))

    assert [item["id"] for item in items] == [1, 2, 3]
    assert len(responses.calls) == 2


@responses.activate
@patch("extract.client.time.sleep")
def test_retries_after_429_then_succeeds(mock_sleep):
    responses.add(
        responses.GET,
        f"{BASE_URL}/teams",
        status=429,
        headers={"Retry-After": "1"},
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/teams",
        json={"data": [{"id": 1}], "meta": {"next_cursor": None, "per_page": 100}},
    )

    items = list(make_client().paginate("/teams"))

    assert [item["id"] for item in items] == [1]
    assert len(responses.calls) == 2
    mock_sleep.assert_any_call(1.0)


@responses.activate
@patch("extract.client.time.sleep")
def test_authorization_header_is_raw_api_key(mock_sleep):
    responses.add(
        responses.GET,
        f"{BASE_URL}/teams",
        json={"data": [], "meta": {"next_cursor": None, "per_page": 100}},
    )

    list(make_client().paginate("/teams"))

    assert responses.calls[0].request.headers["Authorization"] == "test-key"


@patch("extract.client.time.monotonic")
@patch("extract.client.time.sleep")
def test_throttle_waits_out_the_remaining_interval(mock_sleep, mock_monotonic):
    client = make_client()
    client._last_request_at = 100.0
    mock_monotonic.return_value = 105.0  # only 5s elapsed of the required 12s

    client._throttle()

    mock_sleep.assert_called_once_with(7.0)
