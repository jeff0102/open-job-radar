from uuid import uuid4

import pytest
from ats_scrapers import Job
from ats_scrapers.exceptions import ScraperError
from ats_scrapers.scrapers.lever import LeverScraper

from open_job_radar.ingestion import (
    CanonicalJob,
    LeverSourceTenantAdapter,
    SourceTenantAdapter,
    normalize_job,
)


LEVER_RECORD = {
    "id": "lever-123",
    "hostedUrl": "https://jobs.lever.co/acme/lever-123",
    "text": "Platform Engineer",
    "categories": {
        "location": "Remote - Americas",
        "department": "Engineering",
        "team": "Infrastructure",
        "commitment": "Full-time",
    },
    "description": "<p>Build reliable platforms.</p>",
    "applyUrl": "https://jobs.lever.co/acme/lever-123/apply",
    "createdAt": 1767323045000,
    "workplaceType": "remote",
}


class FixtureScraper:
    def __init__(self, records: list[Job] | None = None, error: Exception | None = None) -> None:
        self.records = records or []
        self.error = error

    def fetch(self) -> list[Job]:
        if self.error is not None:
            raise self.error
        return self.records


def lever_job() -> Job:
    return LeverScraper("acme")._parse_job(LEVER_RECORD)


def test_lever_record_is_normalized_by_ats_scrapers() -> None:
    record = lever_job()

    assert isinstance(record, Job)
    assert record.global_id == "lever:lever-123"
    assert record.title == "Platform Engineer"
    assert record.location == "Remote - Americas"
    assert record.is_remote is True
    assert record.department == "Engineering"
    assert record.description == "<p>Build reliable platforms.</p>"


def test_lever_adapter_fetches_records_through_contract_and_maps_canonically() -> None:
    source_tenant_id = uuid4()
    normalized_record = lever_job()
    scraper = FixtureScraper([normalized_record])
    factory_calls: list[tuple[str, float]] = []

    def scraper_factory(slug: str, *, timeout: float) -> FixtureScraper:
        factory_calls.append((slug, timeout))
        return scraper

    adapter = LeverSourceTenantAdapter(
        source_tenant_id,
        "acme",
        timeout=12.5,
        scraper_factory=scraper_factory,
    )

    assert isinstance(adapter, SourceTenantAdapter)
    assert adapter.source_tenant_id == source_tenant_id
    assert adapter.fetch_records() == (normalized_record,)
    assert factory_calls == [("acme", 12.5)]

    canonical = normalize_job(source_tenant_id, normalized_record)

    assert isinstance(canonical, CanonicalJob)
    assert canonical.provider == "lever"
    assert canonical.provider_job_id == "lever-123"
    assert canonical.original_url == "https://jobs.lever.co/acme/lever-123"
    assert canonical.application_url == "https://jobs.lever.co/acme/lever-123/apply"
    assert canonical.title == "Platform Engineer"
    assert canonical.company == "acme"
    assert canonical.location == "Remote - Americas"
    assert canonical.is_remote is True
    assert canonical.provider_data == {
        "categories": {
            "location": "Remote - Americas",
            "department": "Engineering",
            "team": "Infrastructure",
            "commitment": "Full-time",
        },
        "workplaceType": "remote",
    }


def test_lever_adapter_preserves_empty_provider_result() -> None:
    adapter = LeverSourceTenantAdapter(
        uuid4(),
        "acme",
        scraper_factory=lambda slug, *, timeout: FixtureScraper(),
    )

    assert adapter.fetch_records() == ()


def test_lever_adapter_surfaces_provider_failure() -> None:
    provider_error = ScraperError("Lever company acme could not be fetched")
    adapter = LeverSourceTenantAdapter(
        uuid4(),
        "acme",
        scraper_factory=lambda slug, *, timeout: FixtureScraper(error=provider_error),
    )

    with pytest.raises(ScraperError, match="company acme could not be fetched"):
        adapter.fetch_records()
