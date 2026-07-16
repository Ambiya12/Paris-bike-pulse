"""Paris bicycle counter ingestion."""

from collections.abc import Mapping
from dataclasses import dataclass


class BicycleApiResponseError(ValueError):
    """Raised when the bicycle API returns an unexpected response."""


@dataclass(frozen=True, slots=True)
class BicycleApiPage:
    """A validated page of raw bicycle counter records."""

    records: tuple[dict[str, object], ...]
    total_count: int


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
