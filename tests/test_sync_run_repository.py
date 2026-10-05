from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from open_job_radar.persistence import (
    Base,
    SourceTenant,
    SyncRunRepository,
    create_session_factory,
)


def test_sync_run_repository_persists_successful_run() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    source_tenant_id = uuid4()
    started_at = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)
    completed_at = datetime(2026, 10, 5, 15, 2, tzinfo=UTC)

    try:
        with session_factory() as session:
            session.add(
                SourceTenant(
                    id=source_tenant_id,
                    provider="greenhouse",
                    name="Example Careers",
                )
            )
            session.commit()

            repository = SyncRunRepository(session)
            sync_run = repository.create(source_tenant_id, started_at=started_at)
            updated = repository.update(
                sync_run.id,
                status="succeeded",
                completed_at=completed_at,
                message="Fetched 12 jobs.",
            )

            assert updated.source_tenant_id == source_tenant_id
            assert updated.status == "succeeded"
            assert updated.started_at.replace(tzinfo=UTC) == started_at
            assert updated.completed_at.replace(tzinfo=UTC) == completed_at
            assert updated.message == "Fetched 12 jobs."
    finally:
        engine.dispose()


def test_sync_run_repository_persists_failed_run_and_requires_tenant() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            repository = SyncRunRepository(session)
            with pytest.raises(ValueError, match="Source tenant .* does not exist"):
                repository.create(uuid4())

            source_tenant = SourceTenant(
                provider="greenhouse",
                name="Example Careers",
            )
            session.add(source_tenant)
            session.commit()

            sync_run = repository.create(source_tenant.id)
            updated = repository.update(
                sync_run.id,
                status="failed",
                message="Provider request failed.",
            )

            assert updated.source_tenant_id == source_tenant.id
            assert updated.status == "failed"
            assert updated.started_at is not None
            assert updated.completed_at is not None
            assert updated.message == "Provider request failed."
    finally:
        engine.dispose()
