"""Tests for historical weather API response parsing."""

import copy
import json
from pathlib import Path

import pytest

from paris_bike_pulse.ingestion import (
    WeatherApiResponseError,
    parse_weather_api_response,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "weather_api_response.json"


def _fixture_payload() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_parse_weather_api_response_builds_aligned_raw_records() -> None:
    """Aligned hourly arrays become records without business transformations."""
    weather_data = parse_weather_api_response(_fixture_payload())

    assert weather_data.latitude == 48.89279
    assert weather_data.longitude == 2.2920206
    assert weather_data.timezone == "Europe/Paris"
    assert weather_data.hourly_units["temperature_2m"] == "°C"
    assert weather_data.records == (
        {
            "time": "2026-07-01T00:00",
            "temperature_2m": 23.5,
            "relative_humidity_2m": 66,
            "precipitation": 0.0,
            "wind_speed_10m": 8.4,
        },
        {
            "time": "2026-07-01T01:00",
            "temperature_2m": 22.9,
            "relative_humidity_2m": 68,
            "precipitation": 0.1,
            "wind_speed_10m": 7.9,
        },
        {
            "time": "2026-07-01T02:00",
            "temperature_2m": None,
            "relative_humidity_2m": 70,
            "precipitation": 0.0,
            "wind_speed_10m": 7.2,
        },
    )


def test_parse_weather_api_response_rejects_misaligned_hourly_arrays() -> None:
    """Hourly values cannot be paired when array lengths differ."""
    payload = _fixture_payload()
    payload["hourly"]["precipitation"].pop()  # type: ignore[index]

    with pytest.raises(WeatherApiResponseError, match="same number"):
        parse_weather_api_response(payload)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("latitude",), 91, "latitude"),
        (("longitude",), True, "longitude"),
        (("timezone",), " ", "timezone"),
        (("hourly_units", "temperature_2m"), None, "hourly unit"),
        (("hourly", "time"), "not-a-list", "must be a list"),
        (
            ("hourly", "time"),
            ["2026-07-01T00:00", "", "2026-07-01T02:00"],
            "time at index",
        ),
        (("hourly", "precipitation"), [0.0, "rain", 0.0], "numeric or null"),
    ],
)
def test_parse_weather_api_response_rejects_invalid_fields(
    path: tuple[str, ...],
    value: object,
    message: str,
) -> None:
    """Malformed response fields fail before entering the ingestion pipeline."""
    payload = copy.deepcopy(_fixture_payload())
    target = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[assignment,index]
    target[path[-1]] = value

    with pytest.raises(WeatherApiResponseError, match=message):
        parse_weather_api_response(payload)


@pytest.mark.parametrize("payload", [None, [], {}, {"hourly": []}])
def test_parse_weather_api_response_rejects_invalid_envelopes(
    payload: object,
) -> None:
    """Malformed response envelopes fail with the ingestion-specific error."""
    with pytest.raises(WeatherApiResponseError):
        parse_weather_api_response(payload)
