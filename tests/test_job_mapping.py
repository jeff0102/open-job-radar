from uuid import uuid4

import pytest
from ats_scrapers import ATSType, Job
from ats_scrapers.scrapers.greenhouse import GreenhouseScraper

from open_job_radar.ingestion import CanonicalJob, normalize_job


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


def greenhouse_job() -> Job:
    return GreenhouseScraper("acme")._parse_job(GREENHOUSE_RECORD)


def test_greenhouse_job_maps_to_canonical_representation() -> None:
    source_tenant_id = uuid4()

    canonical = normalize_job(source_tenant_id, greenhouse_job())

    assert isinstance(canonical, CanonicalJob)
    assert canonical.source_tenant_id == source_tenant_id
    assert canonical.provider == "greenhouse"
    assert canonical.provider_job_id == "12345"
    assert canonical.original_url == "https://boards.greenhouse.io/acme/jobs/12345"
    assert canonical.application_url is None
    assert canonical.title == "Senior Python Engineer"
    assert canonical.company == "acme"
    assert canonical.location == "Remote - Americas"
    assert canonical.is_remote is None
    assert canonical.description == "<p>Build reliable services.</p>"
    assert canonical.provider_data == {
        "departments": ["Engineering"],
        "offices": ["Remote"],
    }


def test_mapping_preserves_application_url_and_optional_provider_data() -> None:
    source_tenant_id = uuid4()
    job = Job(
        url="https://jobs.example.test/1",
        apply_url="https://apply.example.test/1",
        title="Engineer",
        company="Example",
        ats_type=ATSType.GREENHOUSE,
        ats_id="1",
        is_remote=True,
        raw={"custom_field": {"value": "preserved"}},
    )

    canonical = normalize_job(source_tenant_id, job)

    assert canonical.original_url == "https://jobs.example.test/1"
    assert canonical.application_url == "https://apply.example.test/1"
    assert canonical.is_remote is True
    assert canonical.provider_data == {"custom_field": {"value": "preserved"}}


def test_mapping_handles_missing_optional_fields() -> None:
    job = Job(
        url="https://jobs.example.test/2",
        title="Engineer",
        company="Example",
        ats_type=ATSType.GREENHOUSE,
    )

    canonical = normalize_job(uuid4(), job)

    assert canonical.provider_job_id is None
    assert canonical.location is None
    assert canonical.is_remote is None
    assert canonical.description is None
    assert canonical.application_url is None
    assert canonical.provider_data == {}


def test_canonical_job_rejects_missing_required_text() -> None:
    with pytest.raises(ValueError, match="title must not be blank"):
        CanonicalJob(
            source_tenant_id=uuid4(),
            provider="greenhouse",
            provider_job_id=None,
            original_url="https://jobs.example.test/3",
            title=" ",
            company="Example",
        )
