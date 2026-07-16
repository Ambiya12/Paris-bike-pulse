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
from paris_bike_pulse.ingestion.weather import (
    HOURLY_WEATHER_VARIABLES,
    WeatherApiData,
    WeatherApiResponseError,
    parse_weather_api_response,
)

__all__ = [
    "BicycleApiPage",
    "BicycleApiRequestError",
    "BicycleApiResponseError",
    "BicycleIngestionResult",
    "HOURLY_WEATHER_VARIABLES",
    "WeatherApiData",
    "WeatherApiResponseError",
    "fetch_bicycle_page",
    "ingest_bicycle_records",
    "parse_bicycle_api_response",
    "parse_weather_api_response",
]
