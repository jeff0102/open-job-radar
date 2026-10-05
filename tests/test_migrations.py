from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


PROJECT_ROOT = Path(__file__).parents[1]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_source_tenant_migration_upgrades_and_downgrades_empty_database(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert inspector.get_table_names() == ["alembic_version", "source_tenants"]
        columns = {
            column["name"]: column for column in inspector.get_columns("source_tenants")
        }
        assert set(columns) == {
            "id",
            "provider",
            "name",
            "configuration",
            "enabled",
            "created_at",
            "updated_at",
        }
        assert inspector.get_pk_constraint("source_tenants")["constrained_columns"] == [
            "id"
        ]
    finally:
        engine.dispose()

    command.downgrade(config, "base")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert inspector.get_table_names() == ["alembic_version"]
        with engine.connect() as connection:
            version_count = connection.execute(
                text("SELECT COUNT(*) FROM alembic_version")
            ).scalar_one()
        assert version_count == 0
    finally:
        engine.dispose()
