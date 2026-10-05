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
        provider="fixture",
        provider_job_id=record.external_id,
        original_url=f"https://jobs.example.test/{record.external_id}",
        title="Engineer",
        company="Example",
    )


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, create_session_factory(engine)


def add_source_tenant(session, source_tenant_id):
    session.add(
        SourceTenant(
            id=source_tenant_id,
            provider="fixture",
            name="Example Careers",
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
                    records=(ProviderRecord("job-1"), ProviderRecord("job-2")),
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
