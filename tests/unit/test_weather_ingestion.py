"""Tests for historical weather ingestion orchestration."""

from datetime import date
from unittest.mock import MagicMock

import requests

from paris_bike_pulse.config import load_settings
from paris_bike_pulse.ingestion import WeatherApiData, ingest_hourly_weather
from paris_bike_pulse.ingestion import weather as weather_module


def test_ingest_hourly_weather_returns_fetched_records(
    monkeypatch,
) -> None:
    """The ingestion entry point delegates the requested date range to the client."""
    expected = WeatherApiData(
        records=({"time": "2026-07-01T00:00", "temperature_2m": 23.5},),
        latitude=48.89,
        longitude=2.29,
        timezone="Europe/Paris",
        hourly_units={"time": "iso8601", "temperature_2m": "°C"},
    )
    fetch_weather = MagicMock(return_value=expected)
    monkeypatch.setattr(weather_module, "fetch_hourly_weather", fetch_weather)
    settings = load_settings(env_file=None)
    session = MagicMock(spec=requests.Session)

    result = ingest_hourly_weather(
        settings,
        pipeline_run_id="run-weather-123",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        session=session,
    )

    assert result is expected
    fetch_weather.assert_called_once_with(
        settings,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        session=session,
    )
