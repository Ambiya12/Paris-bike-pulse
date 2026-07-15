"""Tests for application settings."""

from pathlib import Path

import pytest

from paris_bike_pulse.config import load_settings


def test_load_settings_reads_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Environment variables override the local development defaults."""
    monkeypatch.setenv("PARIS_BIKE_PULSE_ENV", "test")
    monkeypatch.setenv("PARIS_BIKE_PULSE_DATA_DIR", "test-data")

    settings = load_settings()

    assert settings.environment == "test"
    assert settings.data_dir == Path("test-data")
