from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from open_job_radar.persistence import Base, SourceTenant


def test_source_tenant_table_defines_stable_required_fields() -> None:
    table = SourceTenant.__table__

    assert table.name == "source_tenants"
    assert [column.name for column in table.primary_key.columns] == ["id"]
    assert table.c.provider.nullable is False
    assert table.c.name.nullable is False
    assert table.c.configuration.nullable is False
    assert table.c.enabled.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_source_tenant_construction_preserves_provider_configuration() -> None:
    configuration = {"board_token": "example", "regions": ["worldwide"]}

    source_tenant = SourceTenant(
        provider="greenhouse",
        name="Example Careers",
        configuration=configuration,
        enabled=False,
    )

    assert source_tenant.provider == "greenhouse"
    assert source_tenant.name == "Example Careers"
    assert source_tenant.configuration == configuration
    assert source_tenant.enabled is False


def test_source_tenant_defaults_are_applied_when_persisted() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            source_tenant = SourceTenant(
                provider="lever",
                name="Example Careers",
            )
            session.add(source_tenant)
            session.commit()
            session.refresh(source_tenant)

            assert source_tenant.id is not None
            assert source_tenant.configuration == {}
            assert source_tenant.enabled is True
            assert source_tenant.created_at is not None
            assert source_tenant.updated_at is not None
    finally:
        engine.dispose()
