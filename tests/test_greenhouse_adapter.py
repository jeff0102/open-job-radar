from datetime import UTC, datetime
from uuid import uuid4

import pytest
from ats_scrapers import Job
from ats_scrapers.exceptions import ScraperError
from ats_scrapers.scrapers.greenhouse import GreenhouseScraper

from open_job_radar.ingestion import (
    GreenhouseSourceTenantAdapter,
    SourceTenantAdapter,
)


GREENHOUSE_RECORD = {
    "id": 12345,
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/12345",
    "title": "Senior Python Engineer",
    "location": {"name": "Remote - Americas"},
    "departments": [{"name": "Engineering"}],
    "offices": [{"name": "Remote"}],
    "content": "&lt;p&gt;Build reliable services.&lt;/p&gt;",
    "first_published": "2026-01-02T03:04:05Z",
    "requisition_id": "REQ-123",
}


class FixtureScraper:
    def __init__(self, records: list[Job] | None = None, error: Exception | None = None) -> None:
        self.records = records or []
        self.error = error

    def fetch(self) -> list[Job]:
        if self.error is not None:
            raise self.error
        return self.records


def test_greenhouse_record_is_normalized_by_ats_scrapers() -> None:
    record = GreenhouseScraper("acme")._parse_job(GREENHOUSE_RECORD)

    assert isinstance(record, Job)
    assert record.global_id == "greenhouse:12345"
    assert record.title == "Senior Python Engineer"
    assert record.location == "Remote - Americas"
    assert record.department == "Engineering"
    assert record.description == "<p>Build reliable services.</p>"
    assert record.posted_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_greenhouse_adapter_fetches_normalized_records_through_contract() -> None:
    source_tenant_id = uuid4()
    normalized_record = GreenhouseScraper("acme")._parse_job(GREENHOUSE_RECORD)
    scraper = FixtureScraper([normalized_record])

    adapter = GreenhouseSourceTenantAdapter(
        source_tenant_id,
        "acme",
        scraper_factory=lambda slug, *, timeout: scraper,
    )

    assert isinstance(adapter, SourceTenantAdapter)
    assert adapter.source_tenant_id == source_tenant_id
    assert adapter.fetch_records() == (normalized_record,)


def test_greenhouse_adapter_preserves_empty_provider_result() -> None:
    adapter = GreenhouseSourceTenantAdapter(
        uuid4(),
        "acme",
        scraper_factory=lambda slug, *, timeout: FixtureScraper(),
    )

    assert adapter.fetch_records() == ()


def test_greenhouse_adapter_surfaces_provider_failure() -> None:
    provider_error = ScraperError("Greenhouse board acme not found")
    adapter = GreenhouseSourceTenantAdapter(
        uuid4(),
        "acme",
        scraper_factory=lambda slug, *, timeout: FixtureScraper(error=provider_error),
    )

    with pytest.raises(ScraperError, match="board acme not found"):
        adapter.fetch_records()
