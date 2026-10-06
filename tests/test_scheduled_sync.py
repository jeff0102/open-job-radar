from uuid import UUID, uuid4

from sqlalchemy import create_engine

from open_job_radar.persistence import Base, SourceTenant, create_session_factory
from open_job_radar.scheduled_sync import main, run_scheduled_synchronization


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
    caplog,
) -> None:
    caplog.set_level("INFO", logger="open_job_radar.scheduled_sync")
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
        success_events = [
            record
            for record in caplog.records
            if record.name == "open_job_radar.scheduled_sync"
            and record.event == "scheduled_synchronization_succeeded"
        ]
        assert len(success_events) == 1
        assert success_events[0].tenant_count == 1
    finally:
        engine.dispose()


def test_scheduled_sync_returns_failure_without_exposing_provider_error(
    capsys,
    caplog,
) -> None:
    caplog.set_level("INFO", logger="open_job_radar.scheduled_sync")
    engine, session_factory = make_session_factory()
    secret = "Authorization: Bearer token=do-not-expose"

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
        assert secret not in caplog.text
        failure_events = [
            record
            for record in caplog.records
            if record.name == "open_job_radar.scheduled_sync"
            and record.event == "scheduled_synchronization_tenant_failed"
        ]
        assert len(failure_events) == 1
        assert failure_events[0].error_type == "RuntimeError"
        assert "Authorization" not in failure_events[0].getMessage()
        assert "Bearer" not in failure_events[0].getMessage()
        assert "token=" not in failure_events[0].getMessage()
        assert any(
            record.event == "scheduled_synchronization_failed"
            for record in caplog.records
        )
    finally:
        engine.dispose()


def test_scheduled_sync_entrypoint_returns_failure_without_exposing_setup_error(
    monkeypatch,
    caplog,
) -> None:
    caplog.set_level("INFO", logger="open_job_radar.scheduled_sync")
    secret = "DATABASE_URL=postgresql://user:password@example.test/jobs"

    def create_engine():
        raise RuntimeError(f"database setup failed: {secret}")

    monkeypatch.setattr(
        "open_job_radar.scheduled_sync.create_database_engine",
        create_engine,
    )

    status = main()

    assert status == 1
    assert secret not in caplog.text
    failure_events = [
        record
        for record in caplog.records
        if record.name == "open_job_radar.scheduled_sync"
        and record.event == "scheduled_synchronization_failed"
    ]
    assert len(failure_events) == 1
    assert failure_events[0].error_type == "RuntimeError"
