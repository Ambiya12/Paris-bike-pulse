"""Tests for structured pipeline logging."""

import json
import logging
from collections.abc import Iterator
from dataclasses import replace
from io import StringIO

import pytest

from paris_bike_pulse.config import load_settings
from paris_bike_pulse.utils import configure_logging, get_pipeline_logger


@pytest.fixture(autouse=True)
def restore_project_logger() -> Iterator[None]:
    """Restore global logging state after each test."""
    project_logger = logging.getLogger("paris_bike_pulse")
    original_handlers = project_logger.handlers.copy()
    original_level = project_logger.level
    original_propagate = project_logger.propagate

    yield

    project_logger.handlers.clear()
    project_logger.handlers.extend(original_handlers)
    project_logger.setLevel(original_level)
    project_logger.propagate = original_propagate


def test_json_logging_includes_pipeline_and_message_context() -> None:
    """JSON logs contain stable fields and merged pipeline context."""
    output = StringIO()
    configure_logging(load_settings(env_file=None), stream=output)
    logger = get_pipeline_logger(
        "ingestion.bicycle",
        pipeline_run_id="run-123",
        source_name="paris-open-data",
    )

    logger.info("Fetched bicycle measurements", extra={"record_count": 25})

    payload = json.loads(output.getvalue())
    assert payload["timestamp"].endswith("Z")
    assert payload["level"] == "INFO"
    assert payload["logger"] == "paris_bike_pulse.ingestion.bicycle"
    assert payload["message"] == "Fetched bicycle measurements"
    assert payload["pipeline_run_id"] == "run-123"
    assert payload["source_name"] == "paris-open-data"
    assert payload["record_count"] == 25


def test_logging_configuration_is_idempotent_and_respects_level() -> None:
    """Repeated configuration does not duplicate records and filters by level."""
    output = StringIO()
    settings = replace(load_settings(env_file=None), log_level="WARNING")
    configure_logging(settings, stream=output)
    configure_logging(settings, stream=output)
    logger = get_pipeline_logger("quality", pipeline_run_id="run-456")

    logger.info("Ignored message")
    logger.warning("Validation failed")

    lines = output.getvalue().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["message"] == "Validation failed"


def test_text_logging_preserves_structured_context() -> None:
    """Readable text output retains pipeline identifiers and record fields."""
    output = StringIO()
    settings = replace(load_settings(env_file=None), log_format="text")
    configure_logging(settings, stream=output)
    logger = get_pipeline_logger("metrics", pipeline_run_id="run-789")

    logger.info("Metrics generated", extra={"metric_count": 4})

    message = output.getvalue()
    assert "INFO paris_bike_pulse.metrics Metrics generated" in message
    assert '"pipeline_run_id": "run-789"' in message
    assert '"metric_count": 4' in message


@pytest.mark.parametrize(("name", "run_id"), [("", "run-1"), ("quality", " ")])
def test_pipeline_logger_rejects_empty_identifiers(name: str, run_id: str) -> None:
    """Loggers require names and pipeline identifiers for traceability."""
    with pytest.raises(ValueError, match="must not be empty"):
        get_pipeline_logger(name, pipeline_run_id=run_id)
