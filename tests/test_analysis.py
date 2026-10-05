from uuid import uuid4

import pytest

from open_job_radar.analysis import RemoteScope, classify_remote_scope
from open_job_radar.ingestion import CanonicalJob


def job(*, location: str | None = None, is_remote: bool | None = None, description: str | None = None) -> CanonicalJob:
    return CanonicalJob(
        source_tenant_id=uuid4(),
        provider="fixture",
        provider_job_id="job-1",
        original_url="https://jobs.example.test/job-1",
        title="Engineer",
        company="Example",
        location=location,
        is_remote=is_remote,
        description=description,
    )


@pytest.mark.parametrize(
    ("location", "is_remote", "description", "expected"),
    [
        ("Remote - Brazil", True, None, RemoteScope.BRAZIL),
        ("Remote - LATAM", True, None, RemoteScope.LATAM),
        ("Remote - Americas", True, None, RemoteScope.AMERICAS),
        ("Worldwide", True, None, RemoteScope.WORLDWIDE),
        ("Remote - US", True, None, RemoteScope.US_ONLY),
        ("US", True, None, RemoteScope.US_ONLY),
        ("Remote - Europe", True, None, RemoteScope.EU_ONLY),
        ("EU", True, None, RemoteScope.EU_ONLY),
        ("New York, NY", False, None, RemoteScope.ONSITE),
        ("Remote - Americas", False, "Hybrid schedule", RemoteScope.HYBRID),
        ("Remote", True, None, RemoteScope.UNKNOWN),
    ],
)
def test_classifies_every_supported_remote_scope(
    location: str,
    is_remote: bool,
    description: str | None,
    expected: RemoteScope,
) -> None:
    assert classify_remote_scope(job(location=location, is_remote=is_remote, description=description)) is expected


def test_hybrid_precedes_geographic_and_worldwide_signals() -> None:
    posting = job(
        location="Remote - Worldwide",
        is_remote=True,
        description="Hybrid role for candidates in Brazil.",
    )

    assert classify_remote_scope(posting) is RemoteScope.HYBRID


def test_onsite_flag_precedes_geographic_remote_scope() -> None:
    posting = job(location="Brazil", is_remote=False)

    assert classify_remote_scope(posting) is RemoteScope.ONSITE


def test_specific_geographic_signals_precede_broader_signals() -> None:
    posting = job(location="Remote - LATAM (including Brazil)", is_remote=True)

    assert classify_remote_scope(posting) is RemoteScope.BRAZIL


@pytest.mark.parametrize(
    "description",
    [
        "Remote and location flexible",
        "Remote role with a global team",
        "Remote in the region to be determined",
    ],
)
def test_ambiguous_remote_wording_is_unknown(description: str) -> None:
    assert classify_remote_scope(job(location="Remote", is_remote=True, description=description)) is RemoteScope.UNKNOWN
