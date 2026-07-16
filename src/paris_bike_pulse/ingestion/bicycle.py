"""Paris bicycle counter ingestion."""

from collections.abc import Mapping
from dataclasses import dataclass

import requests

from paris_bike_pulse.config import Settings
from paris_bike_pulse.utils import get_pipeline_logger

MAX_PAGE_SIZE = 100
MAX_RECORD_WINDOW = 10_000
DEFAULT_MAX_RECORDS = 1_000
DEFAULT_ORDER_BY = "date DESC, id_compteur ASC"


class BicycleApiRequestError(RuntimeError):
    """Raised when a request to the bicycle API fails."""


class BicycleApiResponseError(ValueError):
    """Raised when the bicycle API returns an unexpected response."""


@dataclass(frozen=True, slots=True)
class BicycleApiPage:
    """A validated page of raw bicycle counter records."""

    records: tuple[dict[str, object], ...]
    total_count: int


@dataclass(frozen=True, slots=True)
class BicycleIngestionResult:
    """Records collected by one bounded bicycle ingestion run."""

    records: tuple[dict[str, object], ...]
    total_available: int
    is_complete: bool


def parse_bicycle_api_response(payload: object) -> BicycleApiPage:
    """Validate an API response envelope while preserving raw record fields."""
    if not isinstance(payload, Mapping):
        raise BicycleApiResponseError("bicycle API response must be an object")

    total_count = payload.get("total_count")
    if (
        isinstance(total_count, bool)
        or not isinstance(total_count, int)
        or total_count < 0
    ):
        raise BicycleApiResponseError(
            "bicycle API response total_count must be a non-negative integer"
        )

    results = payload.get("results")
    if not isinstance(results, list):
        raise BicycleApiResponseError("bicycle API response results must be a list")

    records: list[dict[str, object]] = []
    for index, record in enumerate(results):
        if not isinstance(record, Mapping):
            raise BicycleApiResponseError(
                f"bicycle API result at index {index} must be an object"
            )
        records.append(dict(record))

    if total_count < len(records):
        raise BicycleApiResponseError(
            "bicycle API total_count cannot be smaller than the returned page"
        )

    return BicycleApiPage(records=tuple(records), total_count=total_count)


def _validate_page_parameters(limit: int, offset: int) -> None:
    if isinstance(limit, bool) or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
    if isinstance(offset, bool) or offset < 0:
        raise ValueError("offset must be greater than or equal to zero")
    if offset + limit > MAX_RECORD_WINDOW:
        raise ValueError(
            f"offset and limit cannot exceed the {MAX_RECORD_WINDOW}-record API window"
        )


def fetch_bicycle_page(
    settings: Settings,
    *,
    limit: int = MAX_PAGE_SIZE,
    offset: int = 0,
    where: str | None = None,
    order_by: str = DEFAULT_ORDER_BY,
    session: requests.Session | None = None,
) -> BicycleApiPage:
    """Fetch and validate one page of raw Paris bicycle counter records."""
    _validate_page_parameters(limit, offset)
    request_parameters: dict[str, str | int] = {
        "limit": limit,
        "offset": offset,
        "order_by": order_by,
    }
    if where:
        request_parameters["where"] = where

    owns_session = session is None
    http_session = session or requests.Session()
    try:
        response = http_session.get(
            settings.bicycle_api_url,
            params=request_parameters,
            timeout=settings.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise BicycleApiRequestError("request to the bicycle API failed") from error
    finally:
        if owns_session:
            http_session.close()

    try:
        payload = response.json()
    except ValueError as error:
        raise BicycleApiResponseError(
            "bicycle API response did not contain valid JSON"
        ) from error

    return parse_bicycle_api_response(payload)


def _validate_ingestion_parameters(page_size: int, max_records: int) -> None:
    if isinstance(page_size, bool) or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
    if isinstance(max_records, bool) or not 1 <= max_records <= MAX_RECORD_WINDOW:
        raise ValueError(f"max_records must be between 1 and {MAX_RECORD_WINDOW}")


def ingest_bicycle_records(
    settings: Settings,
    *,
    pipeline_run_id: str,
    page_size: int = MAX_PAGE_SIZE,
    max_records: int = DEFAULT_MAX_RECORDS,
    where: str | None = None,
    session: requests.Session | None = None,
) -> BicycleIngestionResult:
    """Collect a bounded, newest-first batch of raw bicycle counter records."""
    _validate_ingestion_parameters(page_size, max_records)
    logger = get_pipeline_logger(
        "ingestion.bicycle",
        pipeline_run_id=pipeline_run_id,
        source_name="paris-open-data",
    )
    records: list[dict[str, object]] = []
    total_available = 0
    offset = 0

    owns_session = session is None
    http_session = session or requests.Session()
    try:
        while len(records) < max_records:
            limit = min(page_size, max_records - len(records))
            page = fetch_bicycle_page(
                settings,
                limit=limit,
                offset=offset,
                where=where,
                session=http_session,
            )
            total_available = page.total_count

            if not page.records:
                if offset < total_available:
                    raise BicycleApiResponseError(
                        "bicycle API returned an empty page before total_count"
                    )
                break

            records.extend(page.records[: max_records - len(records)])
            offset += len(page.records)
            logger.info(
                "Fetched bicycle API page",
                extra={
                    "offset": offset,
                    "page_record_count": len(page.records),
                    "total_available": total_available,
                },
            )

            if offset >= total_available or offset >= MAX_RECORD_WINDOW:
                break
    finally:
        if owns_session:
            http_session.close()

    result = BicycleIngestionResult(
        records=tuple(records),
        total_available=total_available,
        is_complete=len(records) >= total_available,
    )
    logger.info(
        "Bicycle record ingestion completed",
        extra={
            "fetched_record_count": len(result.records),
            "total_available": result.total_available,
            "is_complete": result.is_complete,
        },
    )
    return result
