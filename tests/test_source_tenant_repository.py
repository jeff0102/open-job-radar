from uuid import uuid4

from sqlalchemy import create_engine

from open_job_radar.persistence import Base, SourceTenant, create_session_factory
from open_job_radar.persistence.source_tenant_repository import SourceTenantRepository


def test_source_tenant_repository_returns_persisted_tenant_by_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    source_tenant_id = uuid4()
    configuration = {"board_token": "example"}

    try:
        with session_factory() as session:
            session.add(
                SourceTenant(
                    id=source_tenant_id,
                    provider="greenhouse",
                    name="Example Careers",
                    configuration=configuration,
                    enabled=False,
                )
            )
            session.commit()

        with session_factory() as session:
            result = SourceTenantRepository(session).get_by_id(source_tenant_id)

            assert result is not None
            assert result.id == source_tenant_id
            assert result.provider == "greenhouse"
            assert result.name == "Example Careers"
            assert result.configuration == configuration
            assert result.enabled is False
    finally:
        engine.dispose()


def test_source_tenant_repository_returns_none_for_unknown_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            result = SourceTenantRepository(session).get_by_id(uuid4())

            assert result is None
    finally:
        engine.dispose()
