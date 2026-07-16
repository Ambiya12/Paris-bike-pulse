"""Tests for the historical weather API client."""

import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from paris_bike_pulse.config import load_settings
from paris_bike_pulse.ingestion import (
    WeatherApiRequestError,
    WeatherApiResponseError,
    fetch_hourly_weather,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "weather_api_response.json"


def _response(payload: object) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.json.return_value = payload
    return response


def _fixture_payload() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_fetch_hourly_weather_sends_configured_request() -> None:
    """The client sends an explicit date range, location, units, and timezone."""
    settings = load_settings(env_file=None)
    session = MagicMock(spec=requests.Session)
    session.get.return_value = _response(_fixture_payload())

    weather_data = fetch_hourly_weather(
        settings,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        session=session,
    )

    assert len(weather_data.records) == 3
    session.get.assert_called_once_with(
        settings.weather_api_url,
        params={
            "latitude": 48.8566,
            "longitude": 2.3522,
            "start_date": "2026-07-01",
            "end_date": "2026-07-02",
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
            ),
            "timezone": "Europe/Paris",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
            "wind_speed_unit": "kmh",
        },
        timeout=30.0,
        headers={"Accept": "application/json"},
    )
    session.close.assert_not_called()


@pytest.mark.parametrize(
    ("start_date", "end_date", "error_type"),
    [
        (date(2026, 7, 2), date(2026, 7, 1), ValueError),
        ("2026-07-01", date(2026, 7, 2), TypeError),
        (datetime(2026, 7, 1), date(2026, 7, 2), TypeError),
    ],
)
def test_fetch_hourly_weather_rejects_invalid_date_ranges(
    start_date: object,
    end_date: object,
    error_type: type[Exception],
) -> None:
    """Invalid ranges fail locally before a public request can be made."""
    session = MagicMock(spec=requests.Session)

    with pytest.raises(error_type):
        fetch_hourly_weather(
            load_settings(env_file=None),
            start_date=start_date,  # type: ignore[arg-type]
            end_date=end_date,  # type: ignore[arg-type]
            session=session,
        )

    session.get.assert_not_called()


def test_fetch_hourly_weather_wraps_request_errors() -> None:
    """Network and HTTP failures use a pipeline-specific exception."""
    session = MagicMock(spec=requests.Session)
    session.get.side_effect = requests.Timeout("request timed out")

    with pytest.raises(WeatherApiRequestError) as error_info:
        fetch_hourly_weather(
            load_settings(env_file=None),
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
            session=session,
        )

    assert isinstance(error_info.value.__cause__, requests.Timeout)


def test_fetch_hourly_weather_rejects_invalid_json() -> None:
    """Non-JSON success responses are rejected before parsing weather values."""
    session = MagicMock(spec=requests.Session)
    response = _response(None)
    response.json.side_effect = ValueError("invalid JSON")
    session.get.return_value = response

    with pytest.raises(WeatherApiResponseError, match="valid JSON"):
        fetch_hourly_weather(
            load_settings(env_file=None),
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
            session=session,
        )
