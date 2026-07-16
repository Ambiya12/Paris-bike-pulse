"""External data ingestion."""

from paris_bike_pulse.ingestion.bicycle import (
    BicycleApiPage,
    BicycleApiRequestError,
    BicycleApiResponseError,
    BicycleIngestionResult,
    fetch_bicycle_page,
    ingest_bicycle_records,
    parse_bicycle_api_response,
)

__all__ = [
    "BicycleApiPage",
    "BicycleApiRequestError",
    "BicycleApiResponseError",
    "BicycleIngestionResult",
    "fetch_bicycle_page",
    "ingest_bicycle_records",
    "parse_bicycle_api_response",
]
