"""Tests for the Paris bicycle API client."""

from unittest.mock import MagicMock

import pytest
import requests

from paris_bike_pulse.config import load_settings
from paris_bike_pulse.ingestion import (
    BicycleApiRequestError,
    BicycleApiResponseError,
    fetch_bicycle_page,
)


def _response(payload: object) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.json.return_value = payload
    return response


def test_fetch_bicycle_page_sends_configured_request() -> None:
    """The client uses configured URLs, timeouts, filters, and stable ordering."""
    settings = load_settings(env_file=None)
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(
        {"total_count": 1, "results": [{"id_compteur": "counter-1"}]}
    )

    page = fetch_bicycle_page(
        settings,
        limit=25,
        offset=50,
        where="date >= date'2026-07-01'",
        session=session,
    )

    assert page.total_count == 1
    assert page.records == ({"id_compteur": "counter-1"},)
    session.get.assert_called_once_with(
        settings.bicycle_api_url,
        params={
            "limit": 25,
            "offset": 50,
            "order_by": "date DESC, id_compteur ASC",
            "where": "date >= date'2026-07-01'",
        },
        timeout=settings.request_timeout_seconds,
        headers={"Accept": "application/json"},
    )


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(0, 0), (101, 0), (True, 0), (10, -1), (10, True), (100, 9_901)],
)
def test_fetch_bicycle_page_rejects_invalid_pagination(
    limit: int,
    offset: int,
) -> None:
    """Invalid pagination fails locally before a public API request is sent."""
    with pytest.raises(ValueError):
        fetch_bicycle_page(
            load_settings(env_file=None),
            limit=limit,
            offset=offset,
            session=MagicMock(spec=requests.Session),
        )


def test_fetch_bicycle_page_wraps_request_errors() -> None:
    """Network and HTTP failures use a pipeline-specific exception."""
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = requests.Timeout("request timed out")

    with pytest.raises(BicycleApiRequestError) as error_info:
        fetch_bicycle_page(load_settings(env_file=None), session=session)

    assert isinstance(error_info.value.__cause__, requests.Timeout)


def test_fetch_bicycle_page_rejects_invalid_json() -> None:
    """Non-JSON success responses are rejected before parsing records."""
    session = MagicMock(spec=requests.Session)
    response = _response(None)
    response.json.side_effect = ValueError("invalid JSON")
    session.get.return_value = response

    with pytest.raises(BicycleApiResponseError, match="valid JSON"):
        fetch_bicycle_page(load_settings(env_file=None), session=session)
