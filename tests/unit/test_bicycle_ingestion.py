"""Tests for paginated bicycle counter ingestion."""

from unittest.mock import MagicMock, call

import pytest
import requests

from paris_bike_pulse.config import load_settings
from paris_bike_pulse.ingestion import (
    BicycleApiPage,
    BicycleApiResponseError,
    ingest_bicycle_records,
)
from paris_bike_pulse.ingestion import bicycle as bicycle_module


def _page(total_count: int, *record_ids: str) -> BicycleApiPage:
    return BicycleApiPage(
        records=tuple({"id_compteur": record_id} for record_id in record_ids),
        total_count=total_count,
    )


def test_ingest_bicycle_records_collects_all_filtered_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pagination continues until every record in the filtered result is fetched."""
    fetch_page = MagicMock(side_effect=[_page(3, "one", "two"), _page(3, "three")])
    monkeypatch.setattr(bicycle_module, "fetch_bicycle_page", fetch_page)
    settings = load_settings(env_file=None)
    session = MagicMock(spec=requests.Session)

    result = ingest_bicycle_records(
        settings,
        pipeline_run_id="run-123",
        page_size=2,
        max_records=10,
        where="date >= date'2026-07-01'",
        session=session,
    )

    assert [record["id_compteur"] for record in result.records] == [
        "one",
        "two",
        "three",
    ]
    assert result.total_available == 3
    assert result.is_complete is True
    assert fetch_page.call_args_list == [
        call(
            settings,
            limit=2,
            offset=0,
            where="date >= date'2026-07-01'",
            session=session,
        ),
        call(
            settings,
            limit=2,
            offset=2,
            where="date >= date'2026-07-01'",
            session=session,
        ),
    ]


def test_ingest_bicycle_records_reports_truncated_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured record limit is exact and reported as incomplete."""
    fetch_page = MagicMock(side_effect=[_page(5, "one", "two"), _page(5, "three")])
    monkeypatch.setattr(bicycle_module, "fetch_bicycle_page", fetch_page)

    result = ingest_bicycle_records(
        load_settings(env_file=None),
        pipeline_run_id="run-456",
        page_size=2,
        max_records=3,
        session=MagicMock(spec=requests.Session),
    )

    assert len(result.records) == 3
    assert result.total_available == 5
    assert result.is_complete is False
    assert fetch_page.call_args_list[1].kwargs["limit"] == 1


def test_ingest_bicycle_records_rejects_early_empty_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty page cannot silently truncate an expected result set."""
    monkeypatch.setattr(
        bicycle_module,
        "fetch_bicycle_page",
        MagicMock(return_value=_page(4)),
    )

    with pytest.raises(BicycleApiResponseError, match="empty page"):
        ingest_bicycle_records(
            load_settings(env_file=None),
            pipeline_run_id="run-789",
            session=MagicMock(spec=requests.Session),
        )


@pytest.mark.parametrize(
    ("page_size", "max_records"),
    [(0, 10), (101, 10), (True, 10), (10, 0), (10, 10_001), (10, True)],
)
def test_ingest_bicycle_records_rejects_invalid_bounds(
    page_size: int,
    max_records: int,
) -> None:
    """Configured batches stay inside the public records API limits."""
    with pytest.raises(ValueError):
        ingest_bicycle_records(
            load_settings(env_file=None),
            pipeline_run_id="run-invalid",
            page_size=page_size,
            max_records=max_records,
            session=MagicMock(spec=requests.Session),
        )
