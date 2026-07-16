"""Historical weather response parsing."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime

import requests

from paris_bike_pulse.config import Settings
from paris_bike_pulse.utils import get_pipeline_logger

HOURLY_WEATHER_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
)


class WeatherApiResponseError(ValueError):
    """Raised when the weather API returns an unexpected response."""


class WeatherApiRequestError(RuntimeError):
    """Raised when a request to the weather API fails."""


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


def _validate_date_range(start_date: date, end_date: date) -> None:
    if (
        not isinstance(start_date, date)
        or isinstance(start_date, datetime)
        or not isinstance(end_date, date)
        or isinstance(end_date, datetime)
    ):
        raise TypeError("start_date and end_date must be date values")
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")


def fetch_hourly_weather(
    settings: Settings,
    *,
    start_date: date,
    end_date: date,
    session: requests.Session | None = None,
) -> WeatherApiData:
    """Fetch and validate hourly historical weather for the configured location."""
    _validate_date_range(start_date, end_date)
    request_parameters = {
        "latitude": settings.weather_latitude,
        "longitude": settings.weather_longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": ",".join(HOURLY_WEATHER_VARIABLES),
        "timezone": settings.weather_timezone,
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
        "wind_speed_unit": "kmh",
    }

    owns_session = session is None
    http_session = session or requests.Session()
    try:
        response = http_session.get(
            settings.weather_api_url,
            params=request_parameters,
            timeout=settings.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise WeatherApiRequestError("request to the weather API failed") from error
    finally:
        if owns_session:
            http_session.close()

    try:
        payload = response.json()
    except ValueError as error:
        raise WeatherApiResponseError(
            "weather API response did not contain valid JSON"
        ) from error

    return parse_weather_api_response(payload)


def ingest_hourly_weather(
    settings: Settings,
    *,
    pipeline_run_id: str,
    start_date: date,
    end_date: date,
    session: requests.Session | None = None,
) -> WeatherApiData:
    """Ingest one historical date range and report its collection metadata."""
    logger = get_pipeline_logger(
        "ingestion.weather",
        pipeline_run_id=pipeline_run_id,
        source_name="open-meteo",
    )
    weather_data = fetch_hourly_weather(
        settings,
        start_date=start_date,
        end_date=end_date,
        session=session,
    )
    logger.info(
        "Hourly weather ingestion completed",
        extra={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "record_count": len(weather_data.records),
            "response_latitude": weather_data.latitude,
            "response_longitude": weather_data.longitude,
            "response_timezone": weather_data.timezone,
        },
    )
    return weather_data
