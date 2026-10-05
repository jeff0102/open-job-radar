from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from open_job_radar.ingestion import CanonicalJob
from open_job_radar.persistence import (
    Base,
    JobRepository,
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

            persisted = JobRepository(session).create(canonical_job)
            persisted_id = persisted.id

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
