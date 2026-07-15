"""Environment-backed application settings."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings shared by project components."""

    environment: str
    data_dir: Path


def load_settings() -> Settings:
    """Load settings from environment variables with local defaults."""
    return Settings(
        environment=os.getenv("PARIS_BIKE_PULSE_ENV", "development"),
        data_dir=Path(os.getenv("PARIS_BIKE_PULSE_DATA_DIR", "data")),
    )
