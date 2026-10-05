from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select

from open_job_radar.ingestion import CanonicalJob
from open_job_radar.persistence import (
    Base,
    Job,
    JobRepository,
    JobStatus,
    SourceTenant,
    create_session_factory,
)


def test_job_repository_persists_and_retrieves_canonical_job() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    source_tenant_id = uuid4()
    canonical_job = CanonicalJob(
        source_tenant_id=source_tenant_id,
        provider="greenhouse",
        provider_job_id="12345",
        original_url="https://boards.greenhouse.io/acme/jobs/12345",
        application_url="https://acme.example/apply/12345",
        title="Senior Python Engineer",
        company="Acme",
        location="Remote - Americas",
        is_remote=True,
        description="Build reliable services.",
        provider_data={"requisition_id": "REQ-123"},
    )

    try:
        with session_factory() as session:
            session.add(
                SourceTenant(
                    id=source_tenant_id,
                    provider="greenhouse",
                    name="Acme Careers",
                )
            )
            session.commit()

            repository = JobRepository(session)
            persisted = repository.create(canonical_job)
            persisted_id = persisted.id
            assert persisted.status == JobStatus.NEW

            updated = repository.update_status(persisted_id, JobStatus.APPLIED)
            assert updated.status == JobStatus.APPLIED
            assert repository.get_status(persisted_id) == JobStatus.APPLIED

            with pytest.raises(ValueError, match="Invalid job status"):
                repository.update_status(persisted_id, "not-a-status")

        with session_factory() as session:
            result = JobRepository(session).get_by_id(persisted_id)

            assert result is not None
            assert result.source_tenant_id == source_tenant_id
            assert result.source_tenant.provider == "greenhouse"
            assert result.provider == "greenhouse"
            assert result.provider_job_id == "12345"
            assert result.original_url == canonical_job.original_url
            assert result.application_url == canonical_job.application_url
            assert result.title == canonical_job.title
            assert result.company == canonical_job.company
            assert result.location == canonical_job.location
            assert result.is_remote is True
            assert result.description == canonical_job.description
            assert result.provider_data == canonical_job.provider_data
            assert result.status == JobStatus.APPLIED
            assert JobRepository(session).get_status(persisted_id) == JobStatus.APPLIED
    finally:
        engine.dispose()


def test_job_repository_upsert_is_idempotent_and_refreshes_source_fields() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    source_tenant_id = uuid4()
    initial_job = CanonicalJob(
        source_tenant_id=source_tenant_id,
        provider="greenhouse",
        provider_job_id="12345",
        original_url="https://boards.greenhouse.io/acme/jobs/12345",
        application_url="https://acme.example/apply/12345",
        title="Senior Python Engineer",
        company="Acme",
        location="Remote - Americas",
        is_remote=True,
        description="Build reliable services.",
        provider_data={"requisition_id": "REQ-123"},
    )
    updated_job = CanonicalJob(
        source_tenant_id=source_tenant_id,
        provider="greenhouse",
        provider_job_id="12345",
        original_url="https://boards.greenhouse.io/acme/jobs/12345?updated=true",
        application_url="https://acme.example/apply/updated-12345",
        title="Staff Python Engineer",
        company="Acme Technologies",
        location="Remote - Americas and Europe",
        is_remote=False,
        description="Build and lead reliable services.",
        provider_data={"requisition_id": "REQ-456"},
    )

    try:
        with session_factory() as session:
            session.add(
                SourceTenant(
                    id=source_tenant_id,
                    provider="greenhouse",
                    name="Acme Careers",
                )
            )
            session.commit()

            repository = JobRepository(session)
            first = repository.upsert(initial_job)
            first_id = first.id
            assert session.scalar(select(func.count()).select_from(Job)) == 1

            repeated = repository.upsert(initial_job)
            assert repeated.id == first_id
            assert session.scalar(select(func.count()).select_from(Job)) == 1

            refreshed = repository.upsert(updated_job)
            assert refreshed.id == first_id
            assert refreshed.source_tenant_id == source_tenant_id
            assert refreshed.provider == "greenhouse"
            assert refreshed.provider_job_id == "12345"
            assert refreshed.original_url == updated_job.original_url
            assert refreshed.application_url == updated_job.application_url
            assert refreshed.title == updated_job.title
            assert refreshed.company == updated_job.company
            assert refreshed.location == updated_job.location
            assert refreshed.is_remote is False
            assert refreshed.description == updated_job.description
            assert refreshed.provider_data == updated_job.provider_data
            assert session.scalar(select(func.count()).select_from(Job)) == 1
    finally:
        engine.dispose()


def test_job_repository_rejects_unknown_source_tenant() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    canonical_job = CanonicalJob(
        source_tenant_id=uuid4(),
        provider="greenhouse",
        provider_job_id="12345",
        original_url="https://jobs.example.test/12345",
        title="Engineer",
        company="Example",
    )

    try:
        with session_factory() as session:
            with pytest.raises(ValueError, match="does not exist"):
                JobRepository(session).create(canonical_job)
    finally:
        engine.dispose()
