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
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings shared by project components."""

    environment: str
    data_dir: Path
    bicycle_api_url: str
    weather_api_url: str
    request_timeout_seconds: float

    def __post_init__(self) -> None:
        """Validate values that would otherwise fail during pipeline execution."""
        if not self.environment.strip():
            raise ValueError("PARIS_BIKE_PULSE_ENV must not be empty")

        _validate_http_url("PARIS_BIKE_PULSE_BICYCLE_API_URL", self.bicycle_api_url)
        _validate_http_url("PARIS_BIKE_PULSE_WEATHER_API_URL", self.weather_api_url)

        if (
            not math.isfinite(self.request_timeout_seconds)
            or self.request_timeout_seconds <= 0
        ):
            raise ValueError(
                "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS must be greater than zero"
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
        request_timeout_seconds=_parse_timeout(
            _setting_value(
                "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS",
                str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
                file_values,
            )
        ),
    )
