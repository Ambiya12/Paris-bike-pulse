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

The project foundation currently provides a Python 3.11 package, environment
settings, and development tooling. Data pipelines and analytical features will
be added incrementally.

## Development setup

Python 3.11 is required.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --editable ".[dev]"
```

Use the example file as a template and export its values when custom settings
are needed:

```bash
cp .env.example .env
set -a
source .env
set +a
```

## Quality checks

```bash
ruff check .
ruff format --check .
pytest
```
