"""Tests for application settings."""

from pathlib import Path

import pytest

from paris_bike_pulse.config import load_settings

SETTING_NAMES = (
    "PARIS_BIKE_PULSE_ENV",
    "PARIS_BIKE_PULSE_DATA_DIR",
    "PARIS_BIKE_PULSE_BICYCLE_API_URL",
    "PARIS_BIKE_PULSE_WEATHER_API_URL",
    "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS",
    "PARIS_BIKE_PULSE_LOG_LEVEL",
    "PARIS_BIKE_PULSE_LOG_FORMAT",
)


def _clear_setting_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_load_settings_uses_development_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Development defaults provide a usable local configuration."""
    _clear_setting_variables(monkeypatch)

    settings = load_settings(env_file=None)

    assert settings.environment == "development"
    assert settings.data_dir == Path("data")
    assert settings.bicycle_api_url.startswith("https://opendata.paris.fr/")
    assert settings.weather_api_url == "https://archive-api.open-meteo.com/v1/archive"
    assert settings.request_timeout_seconds == 30.0
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"
    assert settings.bronze_dir == Path("data/bronze")
    assert settings.silver_dir == Path("data/silver")
    assert settings.gold_dir == Path("data/gold")


def test_load_settings_reads_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Process environment variables override development defaults."""
    monkeypatch.setenv("PARIS_BIKE_PULSE_ENV", "test")
    monkeypatch.setenv("PARIS_BIKE_PULSE_DATA_DIR", "test-data")
    monkeypatch.setenv(
        "PARIS_BIKE_PULSE_BICYCLE_API_URL", "https://example.test/bicycles"
    )
    monkeypatch.setenv(
        "PARIS_BIKE_PULSE_WEATHER_API_URL", "https://example.test/weather"
    )
    monkeypatch.setenv("PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("PARIS_BIKE_PULSE_LOG_LEVEL", "debug")
    monkeypatch.setenv("PARIS_BIKE_PULSE_LOG_FORMAT", "TEXT")

    settings = load_settings(env_file=None)

    assert settings.environment == "test"
    assert settings.data_dir == Path("test-data")
    assert settings.bicycle_api_url == "https://example.test/bicycles"
    assert settings.weather_api_url == "https://example.test/weather"
    assert settings.request_timeout_seconds == 12.5
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "text"


def test_load_settings_reads_dotenv_without_overriding_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A local dotenv file supplies values below process-environment priority."""
    _clear_setting_variables(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PARIS_BIKE_PULSE_ENV=local\n"
        "PARIS_BIKE_PULSE_DATA_DIR=local-data\n"
        "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS=45\n"
        "PARIS_BIKE_PULSE_LOG_LEVEL=WARNING\n"
        "PARIS_BIKE_PULSE_LOG_FORMAT=text\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PARIS_BIKE_PULSE_ENV", "test")

    settings = load_settings(env_file=env_file)

    assert settings.environment == "test"
    assert settings.data_dir == Path("local-data")
    assert settings.request_timeout_seconds == 45.0
    assert settings.log_level == "WARNING"
    assert settings.log_format == "text"


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("PARIS_BIKE_PULSE_ENV", " ", "must not be empty"),
        (
            "PARIS_BIKE_PULSE_BICYCLE_API_URL",
            "not-a-url",
            "must be a valid HTTP or HTTPS URL",
        ),
        (
            "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS",
            "invalid",
            "must be a number",
        ),
        (
            "PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS",
            "0",
            "must be greater than zero",
        ),
        (
            "PARIS_BIKE_PULSE_LOG_LEVEL",
            "verbose",
            "must be one of",
        ),
        (
            "PARIS_BIKE_PULSE_LOG_FORMAT",
            "yaml",
            "must be one of",
        ),
    ],
)
def test_load_settings_rejects_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
    message: str,
) -> None:
    """Invalid external configuration fails with an actionable error."""
    _clear_setting_variables(monkeypatch)
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=message):
        load_settings(env_file=None)
