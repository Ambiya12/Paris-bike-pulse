"""Environment-backed application settings."""

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

DEFAULT_BICYCLE_API_URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/"
    "comptage-velo-donnees-compteurs/records"
)
DEFAULT_WEATHER_API_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_WEATHER_LATITUDE = 48.8566
DEFAULT_WEATHER_LONGITUDE = 2.3522
DEFAULT_WEATHER_TIMEZONE = "Europe/Paris"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0
VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
VALID_LOG_FORMATS = frozenset({"json", "text"})


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings shared by project components."""

    environment: str
    data_dir: Path
    bicycle_api_url: str
    weather_api_url: str
    weather_latitude: float
    weather_longitude: float
    weather_timezone: str
    request_timeout_seconds: float
    log_level: str
    log_format: str

    def __post_init__(self) -> None:
        """Validate values that would otherwise fail during pipeline execution."""
        if not self.environment.strip():
            raise ValueError("PARIS_BIKE_PULSE_ENV must not be empty")

        _validate_http_url("PARIS_BIKE_PULSE_BICYCLE_API_URL", self.bicycle_api_url)
        _validate_http_url("PARIS_BIKE_PULSE_WEATHER_API_URL", self.weather_api_url)

        if (
            not math.isfinite(self.weather_latitude)
            or not -90 <= self.weather_latitude <= 90
        ):
            raise ValueError(
                "PARIS_BIKE_PULSE_WEATHER_LATITUDE must be between -90 and 90"
            )

        if (
            not math.isfinite(self.weather_longitude)
            or not -180 <= self.weather_longitude <= 180
        ):
            raise ValueError(
                "PARIS_BIKE_PULSE_WEATHER_LONGITUDE must be between -180 and 180"
            )

        if not self.weather_timezone.strip():
            raise ValueError("PARIS_BIKE_PULSE_WEATHER_TIMEZONE must not be empty")

        if (
            not math.isfinite(self.request_timeout_seconds)
            or self.request_timeout_seconds <= 0
        ):
            raise ValueError(
                "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS must be greater than zero"
            )

        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError(
                "PARIS_BIKE_PULSE_LOG_LEVEL must be one of "
                f"{', '.join(sorted(VALID_LOG_LEVELS))}"
            )

        if self.log_format not in VALID_LOG_FORMATS:
            raise ValueError(
                "PARIS_BIKE_PULSE_LOG_FORMAT must be one of "
                f"{', '.join(sorted(VALID_LOG_FORMATS))}"
            )

    @property
    def bronze_dir(self) -> Path:
        """Return the local Bronze-layer directory."""
        return self.data_dir / "bronze"

    @property
    def silver_dir(self) -> Path:
        """Return the local Silver-layer directory."""
        return self.data_dir / "silver"

    @property
    def gold_dir(self) -> Path:
        """Return the local Gold-layer directory."""
        return self.data_dir / "gold"


def _validate_http_url(setting_name: str, value: str) -> None:
    parsed_url = urlparse(value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError(f"{setting_name} must be a valid HTTP or HTTPS URL")


def _setting_value(
    name: str,
    default: str,
    file_values: Mapping[str, str | None],
) -> str:
    if name in os.environ:
        return os.environ[name]

    file_value = file_values.get(name)
    return default if file_value is None else file_value


def _parse_timeout(value: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(
            "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS must be a number"
        ) from error


def _parse_float(setting_name: str, value: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{setting_name} must be a number") from error


def _parse_log_level(value: str) -> str:
    return value.strip().upper()


def _parse_log_format(value: str) -> str:
    return value.strip().lower()


def load_settings(env_file: str | Path | None = ".env") -> Settings:
    """Load settings from process variables, an optional file, and defaults."""
    file_values = {} if env_file is None else dotenv_values(env_file)

    return Settings(
        environment=_setting_value("PARIS_BIKE_PULSE_ENV", "development", file_values),
        data_dir=Path(_setting_value("PARIS_BIKE_PULSE_DATA_DIR", "data", file_values)),
        bicycle_api_url=_setting_value(
            "PARIS_BIKE_PULSE_BICYCLE_API_URL",
            DEFAULT_BICYCLE_API_URL,
            file_values,
        ),
        weather_api_url=_setting_value(
            "PARIS_BIKE_PULSE_WEATHER_API_URL",
            DEFAULT_WEATHER_API_URL,
            file_values,
        ),
        weather_latitude=_parse_float(
            "PARIS_BIKE_PULSE_WEATHER_LATITUDE",
            _setting_value(
                "PARIS_BIKE_PULSE_WEATHER_LATITUDE",
                str(DEFAULT_WEATHER_LATITUDE),
                file_values,
            ),
        ),
        weather_longitude=_parse_float(
            "PARIS_BIKE_PULSE_WEATHER_LONGITUDE",
            _setting_value(
                "PARIS_BIKE_PULSE_WEATHER_LONGITUDE",
                str(DEFAULT_WEATHER_LONGITUDE),
                file_values,
            ),
        ),
        weather_timezone=_setting_value(
            "PARIS_BIKE_PULSE_WEATHER_TIMEZONE",
            DEFAULT_WEATHER_TIMEZONE,
            file_values,
        ).strip(),
        request_timeout_seconds=_parse_timeout(
            _setting_value(
                "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS",
                str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
                file_values,
            )
        ),
        log_level=_parse_log_level(
            _setting_value("PARIS_BIKE_PULSE_LOG_LEVEL", "INFO", file_values)
        ),
        log_format=_parse_log_format(
            _setting_value("PARIS_BIKE_PULSE_LOG_FORMAT", "json", file_values)
        ),
    )
