"""Historical weather response parsing."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

HOURLY_WEATHER_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
)


class WeatherApiResponseError(ValueError):
    """Raised when the weather API returns an unexpected response."""


@dataclass(frozen=True, slots=True)
class WeatherApiData:
    """Validated weather response with API-native hourly records."""

    records: tuple[dict[str, object], ...]
    latitude: float
    longitude: float
    timezone: str
    hourly_units: dict[str, str]


def _parse_coordinate(
    payload: Mapping[object, object],
    name: str,
    minimum: float,
    maximum: float,
) -> float:
    value = payload.get(name)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise WeatherApiResponseError(
            f"weather API response {name} must be between {minimum} and {maximum}"
        )
    return float(value)


def _parse_units(payload: Mapping[object, object]) -> dict[str, str]:
    units = payload.get("hourly_units")
    if not isinstance(units, Mapping):
        raise WeatherApiResponseError(
            "weather API response hourly_units must be an object"
        )

    required_fields = ("time", *HOURLY_WEATHER_VARIABLES)
    parsed_units: dict[str, str] = {}
    for field in required_fields:
        unit = units.get(field)
        if not isinstance(unit, str) or not unit.strip():
            raise WeatherApiResponseError(
                f"weather API hourly unit for {field} must be a non-empty string"
            )
        parsed_units[field] = unit
    return parsed_units


def _parse_hourly_arrays(payload: Mapping[object, object]) -> dict[str, list[object]]:
    hourly = payload.get("hourly")
    if not isinstance(hourly, Mapping):
        raise WeatherApiResponseError("weather API response hourly must be an object")

    required_fields = ("time", *HOURLY_WEATHER_VARIABLES)
    arrays: dict[str, list[object]] = {}
    for field in required_fields:
        values = hourly.get(field)
        if not isinstance(values, list):
            raise WeatherApiResponseError(
                f"weather API hourly field {field} must be a list"
            )
        arrays[field] = values

    expected_length = len(arrays["time"])
    if any(len(values) != expected_length for values in arrays.values()):
        raise WeatherApiResponseError(
            "weather API hourly fields must contain the same number of values"
        )
    return arrays


def _validate_hourly_values(arrays: Mapping[str, list[object]]) -> None:
    for index, timestamp in enumerate(arrays["time"]):
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise WeatherApiResponseError(
                f"weather API time at index {index} must be a non-empty string"
            )

    for field in HOURLY_WEATHER_VARIABLES:
        for index, value in enumerate(arrays[field]):
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise WeatherApiResponseError(
                    f"weather API {field} at index {index} must be numeric or null"
                )


def parse_weather_api_response(payload: object) -> WeatherApiData:
    """Validate an Open-Meteo response and create aligned hourly records."""
    if not isinstance(payload, Mapping):
        raise WeatherApiResponseError("weather API response must be an object")

    latitude = _parse_coordinate(payload, "latitude", -90, 90)
    longitude = _parse_coordinate(payload, "longitude", -180, 180)

    timezone = payload.get("timezone")
    if not isinstance(timezone, str) or not timezone.strip():
        raise WeatherApiResponseError(
            "weather API response timezone must be a non-empty string"
        )

    hourly_units = _parse_units(payload)
    arrays = _parse_hourly_arrays(payload)
    _validate_hourly_values(arrays)

    records = tuple(
        {field: arrays[field][index] for field in arrays}
        for index in range(len(arrays["time"]))
    )
    return WeatherApiData(
        records=records,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        hourly_units=hourly_units,
    )
