from uuid import UUID, uuid4

from sqlalchemy import create_engine

from open_job_radar.persistence import Base, SourceTenant, create_session_factory
from open_job_radar.scheduled_sync import run_scheduled_synchronization


def make_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, create_session_factory(engine)


def add_tenant(session, *, enabled: bool = True) -> UUID:
    tenant_id = uuid4()
    session.add(
        SourceTenant(
            id=tenant_id,
            provider="fixture",
            name="Fixture source",
            enabled=enabled,
        )
    )
    session.commit()
    return tenant_id


def test_scheduled_sync_runs_existing_orchestration_for_enabled_tenants(
    monkeypatch,
) -> None:
    engine, session_factory = make_session_factory()
    synchronized_tenants: list[UUID] = []

    try:
        with session_factory() as session:
            enabled_id = add_tenant(session)
            add_tenant(session, enabled=False)

        def synchronize_tenant(session, source_tenant_id):
            synchronized_tenants.append(source_tenant_id)

        monkeypatch.setattr(
            "open_job_radar.scheduled_sync.synchronize_source_tenant",
            synchronize_tenant,
        )

        status = run_scheduled_synchronization(session_factory)

        assert status == 0
        assert synchronized_tenants == [enabled_id]
    finally:
        engine.dispose()


def test_scheduled_sync_returns_failure_without_exposing_provider_error(
    capsys,
) -> None:
    engine, session_factory = make_session_factory()
    secret = "token=do-not-expose"

    try:
        with session_factory() as session:
            add_tenant(session)

        def synchronize_tenant(session, source_tenant_id):
            raise RuntimeError(f"provider request failed: {secret}")

        status = run_scheduled_synchronization(
            session_factory,
            synchronize_tenant=synchronize_tenant,
        )

        captured = capsys.readouterr()
        assert status != 0
        assert secret not in captured.out
        assert secret not in captured.err
    finally:
        engine.dispose()
