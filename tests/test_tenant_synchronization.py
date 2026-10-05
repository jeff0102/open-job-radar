from uuid import uuid4

from sqlalchemy import create_engine, select

from open_job_radar.ingestion import (
    DjinniSourceTenantAdapter,
    create_source_tenant_adapter,
    synchronize_source_tenant,
)
from open_job_radar.persistence import Base, Job, SourceTenant, create_session_factory

from test_djinni_adapter import DJINNI_PAYLOAD, FixtureFetcher


def test_tenant_configuration_builds_djinni_adapter() -> None:
    source_tenant = SourceTenant(
        id=uuid4(),
        provider="djinni",
        name="Djinni feed",
        configuration={"feed_url": "https://djinni.example.test/jobs.json"},
    )

    adapter = create_source_tenant_adapter(
        source_tenant,
        djinni_fetcher_factory=lambda feed_url, *, timeout: FixtureFetcher(
            (DJINNI_PAYLOAD,)
        ),
    )

    assert isinstance(adapter, DjinniSourceTenantAdapter)
    assert adapter.source_tenant_id == source_tenant.id


def test_tenant_driven_djinni_sync_persists_canonical_job() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    source_tenant_id = uuid4()

    try:
        with session_factory() as session:
            session.add(
                SourceTenant(
                    id=source_tenant_id,
                    provider="djinni",
                    name="Djinni feed",
                    configuration={"feed_url": "https://djinni.example.test/jobs.json"},
                )
            )
            session.commit()

            sync_run = synchronize_source_tenant(
                session,
                source_tenant_id,
                djinni_fetcher_factory=lambda feed_url, *, timeout: FixtureFetcher(
                    (DJINNI_PAYLOAD,)
                ),
            )

            job = session.scalar(select(Job))
            assert sync_run.status == "succeeded"
            assert sync_run.message == "Synchronized 1 jobs."
            assert job is not None
            assert job.provider == "djinni"
            assert job.provider_job_id == "987654"
            assert job.original_url == DJINNI_PAYLOAD["url"]
            assert job.title == "Senior Python Engineer"
            assert job.company == "Acme Labs"
            assert job.location == "Remote - LATAM"
            assert job.is_remote is True
    finally:
        engine.dispose()
