# Paris Bike Pulse

Paris Bike Pulse is an end-to-end data engineering and machine-learning
project for analyzing bicycle traffic in Paris.

The platform will ingest bicycle counter and weather data, apply data-quality
controls, create business-ready metrics, and provide a dashboard for exploring
cycling patterns. It will also compare simple forecasting baselines with a
machine-learning model that estimates bicycle traffic one hour ahead.

## Project goals

- Build reproducible data pipelines with Python, PySpark, and SQL
- Apply a Bronze, Silver, and Gold data architecture
- Monitor data quality and freshness
- Analyze bicycle activity by time, location, and weather conditions
- Forecast bicycle traffic using time-based features
- Track model experiments with MLflow

## Current status

The project foundation currently provides a Python 3.11 package, validated
environment settings, and development tooling. Data pipelines and analytical
features will be added incrementally.

## Development setup

Python 3.11 is required.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --editable ".[dev]"
```

Use the example file as a template when custom settings are needed. Values from
the process environment take precedence over values in `.env`.

```bash
cp .env.example .env
```

## Application configuration

The application supports the following settings:

| Variable | Purpose | Default |
| --- | --- | --- |
| `PARIS_BIKE_PULSE_ENV` | Runtime environment name | `development` |
| `PARIS_BIKE_PULSE_DATA_DIR` | Root directory for local datasets | `data` |
| `PARIS_BIKE_PULSE_BICYCLE_API_URL` | Paris bicycle counter API endpoint | Paris Open Data |
| `PARIS_BIKE_PULSE_WEATHER_API_URL` | Historical weather API endpoint | Open-Meteo archive |
| `PARIS_BIKE_PULSE_WEATHER_LATITUDE` | Weather query latitude | `48.8566` |
| `PARIS_BIKE_PULSE_WEATHER_LONGITUDE` | Weather query longitude | `2.3522` |
| `PARIS_BIKE_PULSE_WEATHER_TIMEZONE` | Weather response timezone | `Europe/Paris` |
| `PARIS_BIKE_PULSE_REQUEST_TIMEOUT_SECONDS` | External request timeout | `30` |
| `PARIS_BIKE_PULSE_LOG_LEVEL` | Minimum application log level | `INFO` |
| `PARIS_BIKE_PULSE_LOG_FORMAT` | Log output format (`json` or `text`) | `json` |

Bronze, Silver, and Gold directories are derived from the configured data root.

## Structured logging

Pipeline logs can be emitted as JSON for automated processing or as readable
text for local development. Every pipeline logger requires a run identifier and
can include source-level or message-level context.

```python
from paris_bike_pulse.config import load_settings
from paris_bike_pulse.utils import configure_logging, get_pipeline_logger

settings = load_settings()
configure_logging(settings)

logger = get_pipeline_logger(
    "ingestion.bicycle",
    pipeline_run_id="2026-07-16T08:00:00Z",
    source_name="paris-open-data",
)
logger.info("Ingestion completed", extra={"record_count": 120})
```

## Bicycle counter ingestion

The bicycle client retrieves raw counter records from Paris Open Data in stable,
newest-first pages. Ingestion is bounded and reports whether the available
filtered result was fully collected, so record limits never cause silent data
loss.

```python
from paris_bike_pulse.config import load_settings
from paris_bike_pulse.ingestion import ingest_bicycle_records

settings = load_settings()
result = ingest_bicycle_records(
    settings,
    pipeline_run_id="2026-07-16-bicycle-ingestion",
    max_records=5_000,
    where="date >= date'2026-07-15' AND date < date'2026-07-16'",
)

print(len(result.records), result.is_complete)
```

The public records endpoint limits a query window to 10,000 rows. Incremental
date filters should therefore be used for normal pipeline runs. Raw records are
kept unchanged for the future Bronze storage layer.

## Quality checks

```bash
ruff check .
ruff format --check .
pytest
```
