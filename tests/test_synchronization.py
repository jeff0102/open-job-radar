from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select

from open_job_radar.ingestion import CanonicalJob, SynchronizationService
from open_job_radar.persistence import (
    Base,
    Job,
    SourceTenant,
    SyncRun,
    create_session_factory,
)


@dataclass(frozen=True)
class ProviderRecord:
    external_id: str
    provider: str = "fixture"
    title: str = "Engineer"
    company: str = "Example"
    location: str | None = "Remote - Americas"
    original_url: str | None = None
    application_url: str | None = None
    provider_data: dict[str, object] | None = None


class FixtureAdapter:
    def __init__(self, source_tenant_id, records=(), error=None) -> None:
        self._source_tenant_id = source_tenant_id
        self._records = records
        self._error = error

    @property
    def source_tenant_id(self):
        return self._source_tenant_id

    def fetch_records(self):
        if self._error is not None:
            raise self._error
        return self._records


def canonical_job(source_tenant_id, record: ProviderRecord) -> CanonicalJob:
    return CanonicalJob(
        source_tenant_id=source_tenant_id,
        provider=record.provider,
        provider_job_id=record.external_id,
        original_url=(
            record.original_url or f"https://jobs.example.test/{record.external_id}"
        ),
        application_url=record.application_url,
        title=record.title,
        company=record.company,
        location=record.location,
        provider_data=record.provider_data or {},
    )


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, create_session_factory(engine)


def add_source_tenant(session, source_tenant_id, provider="fixture"):
    session.add(
        SourceTenant(
            id=source_tenant_id,
            provider=provider,
            name=f"{provider.title()} Careers",
        )
    )
    session.commit()


def test_synchronization_records_success_and_persists_jobs() -> None:
    engine, session_factory = make_session()
    source_tenant_id = uuid4()

    try:
        with session_factory() as session:
            add_source_tenant(session, source_tenant_id)
            service = SynchronizationService(
                session,
                FixtureAdapter(
                    source_tenant_id,
                    records=(
                        ProviderRecord("job-1"),
                        ProviderRecord("job-2", title="Staff Engineer"),
                    ),
                ),
                mapper=canonical_job,
            )

            sync_run = service.synchronize()

            assert sync_run.status == "succeeded"
            assert sync_run.started_at is not None
            assert sync_run.completed_at is not None
            assert sync_run.completed_at >= sync_run.started_at
            assert sync_run.message == "Synchronized 2 jobs."
            assert session.scalar(select(func.count()).select_from(Job)) == 2
    finally:
        engine.dispose()


def test_synchronization_records_one_failed_run_and_reraises_adapter_error() -> None:
    engine, session_factory = make_session()
    source_tenant_id = uuid4()
    provider_error = RuntimeError("request token=do-not-store")

    try:
        with session_factory() as session:
            add_source_tenant(session, source_tenant_id)
            service = SynchronizationService(
                session,
                FixtureAdapter(source_tenant_id, error=provider_error),
                mapper=canonical_job,
            )

            with pytest.raises(RuntimeError) as raised:
                service.synchronize()

            assert raised.value is provider_error
            failed_runs = session.scalars(
                select(SyncRun).where(SyncRun.source_tenant_id == source_tenant_id)
            ).all()
            assert len(failed_runs) == 1
            failed_run = failed_runs[0]
            assert failed_run.status == "failed"
            assert failed_run.started_at is not None
            assert failed_run.completed_at is not None
            assert failed_run.completed_at >= failed_run.started_at
            assert failed_run.message == (
                "Synchronization failed during adapter fetch (RuntimeError)."
            )
            assert "do-not-store" not in failed_run.message
    finally:
        engine.dispose()


def test_synchronization_deduplicates_equivalent_jobs_across_providers() -> None:
    engine, session_factory = make_session()
    greenhouse_tenant_id = uuid4()
    lever_tenant_id = uuid4()

    try:
        with session_factory() as session:
            add_source_tenant(session, greenhouse_tenant_id, "greenhouse")
            add_source_tenant(session, lever_tenant_id, "lever")
            greenhouse_record = ProviderRecord(
                "greenhouse-1",
                provider="greenhouse",
                original_url="https://boards.greenhouse.io/acme/jobs/1",
                application_url="https://boards.greenhouse.io/acme/jobs/1#apply",
                provider_data={"requisition_id": "REQ-1"},
            )
            lever_record = ProviderRecord(
                "lever-1",
                provider="lever",
                original_url="https://jobs.lever.co/acme/lever-1",
                application_url="https://jobs.lever.co/acme/lever-1/apply",
                provider_data={"workplaceType": "remote"},
            )

            greenhouse_job = SynchronizationService(
                session,
                FixtureAdapter(greenhouse_tenant_id, (greenhouse_record,)),
                mapper=canonical_job,
            ).synchronize()
            first_job = session.scalar(select(Job))
            SynchronizationService(
                session,
                FixtureAdapter(lever_tenant_id, (lever_record,)),
                mapper=canonical_job,
            ).synchronize()

            merged_job = session.scalar(select(Job))
            assert greenhouse_job.status == "succeeded"
            assert merged_job is not None
            assert first_job is not None
            assert merged_job.id == first_job.id
            assert session.scalar(select(func.count()).select_from(Job)) == 1
            assert merged_job.original_url == greenhouse_record.original_url
            assert merged_job.provider_data["sources"] == [
                {
                    "source_tenant_id": str(greenhouse_tenant_id),
                    "provider": "greenhouse",
                    "provider_job_id": "greenhouse-1",
                    "original_url": greenhouse_record.original_url,
                    "application_url": greenhouse_record.application_url,
                    "provider_data": greenhouse_record.provider_data,
                },
                {
                    "source_tenant_id": str(lever_tenant_id),
                    "provider": "lever",
                    "provider_job_id": "lever-1",
                    "original_url": lever_record.original_url,
                    "application_url": lever_record.application_url,
                    "provider_data": lever_record.provider_data,
                },
            ]
    finally:
        engine.dispose()


def test_synchronization_keeps_distinct_postings_separate() -> None:
    engine, session_factory = make_session()
    first_tenant_id = uuid4()
    second_tenant_id = uuid4()

    try:
        with session_factory() as session:
            add_source_tenant(session, first_tenant_id, "greenhouse")
            add_source_tenant(session, second_tenant_id, "lever")
            first_record = ProviderRecord("first", provider="greenhouse")
            second_record = ProviderRecord(
                "second",
                provider="lever",
                location="Remote - EU",
            )
            SynchronizationService(
                session,
                FixtureAdapter(first_tenant_id, (first_record,)),
                mapper=canonical_job,
            ).synchronize()
            SynchronizationService(
                session,
                FixtureAdapter(second_tenant_id, (second_record,)),
                mapper=canonical_job,
            ).synchronize()

            assert session.scalar(select(func.count()).select_from(Job)) == 2
    finally:
        engine.dispose()


def test_synchronization_repeated_cross_provider_sync_is_idempotent() -> None:
    engine, session_factory = make_session()
    first_tenant_id = uuid4()
    second_tenant_id = uuid4()

    try:
        with session_factory() as session:
            add_source_tenant(session, first_tenant_id, "greenhouse")
            add_source_tenant(session, second_tenant_id, "lever")
            first_record = ProviderRecord(
                "first",
                provider="greenhouse",
                provider_data={"version": 1},
            )
            second_record = ProviderRecord(
                "second",
                provider="lever",
                provider_data={"version": 1},
            )
            for tenant_id, record in (
                (first_tenant_id, first_record),
                (second_tenant_id, second_record),
                (first_tenant_id, first_record),
                (second_tenant_id, second_record),
            ):
                SynchronizationService(
                    session,
                    FixtureAdapter(tenant_id, (record,)),
                    mapper=canonical_job,
                ).synchronize()

            job = session.scalar(select(Job))
            assert job is not None
            assert session.scalar(select(func.count()).select_from(Job)) == 1
            assert len(job.provider_data["sources"]) == 2
    finally:
        engine.dispose()
