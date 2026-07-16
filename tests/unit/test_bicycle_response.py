"""Tests for Paris bicycle API response parsing."""

import json
from pathlib import Path

import pytest

from paris_bike_pulse.ingestion import (
    BicycleApiResponseError,
    parse_bicycle_api_response,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "bicycle_api_page.json"


def test_parse_bicycle_api_response_preserves_raw_records() -> None:
    """Valid API records remain unchanged for later Bronze storage."""
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    page = parse_bicycle_api_response(payload)

    assert page.total_count == 2
    assert len(page.records) == 2
    assert page.records[0]["id_compteur"] == "100056038-101056038"
    assert page.records[0]["sum_counts"] == 69
    assert page.records[0]["coordinates"] == {
        "lon": 2.30743,
        "lat": 48.86999,
    }


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"total_count": -1, "results": []},
        {"total_count": True, "results": []},
        {"total_count": 1, "results": {}},
        {"total_count": 1, "results": ["not-a-record"]},
        {"total_count": 0, "results": [{"id_compteur": "counter-1"}]},
    ],
)
def test_parse_bicycle_api_response_rejects_invalid_envelopes(
    payload: object,
) -> None:
    """Malformed API envelopes fail before records enter the pipeline."""
    with pytest.raises(BicycleApiResponseError):
        parse_bicycle_api_response(payload)
