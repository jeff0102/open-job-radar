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
        assert inspector.get_table_names() == [
            "alembic_version",
            "jobs",
            "source_tenants",
            "sync_runs",
        ]
        source_tenant_columns = {
            column["name"]
            for column in inspector.get_columns("source_tenants")
        }
        assert source_tenant_columns == {
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
        job_columns = {
            column["name"] for column in inspector.get_columns("jobs")
        }
        assert job_columns == {
            "id",
            "source_tenant_id",
            "provider",
            "provider_job_id",
            "original_url",
            "application_url",
            "title",
            "company",
            "location",
            "is_remote",
            "description",
            "provider_data",
            "created_at",
            "updated_at",
        }
        sync_run_columns = {
            column["name"]: column
            for column in inspector.get_columns("sync_runs")
        }
        assert set(sync_run_columns) == {
            "id",
            "source_tenant_id",
            "status",
            "started_at",
            "completed_at",
            "message",
        }
        assert sync_run_columns["completed_at"]["nullable"] is True
        assert sync_run_columns["message"]["nullable"] is True
        assert inspector.get_pk_constraint("sync_runs")["constrained_columns"] == [
            "id"
        ]
        assert inspector.get_foreign_keys("sync_runs")[0]["referred_table"] == (
            "source_tenants"
        )
        assert inspector.get_pk_constraint("jobs")["constrained_columns"] == ["id"]
        assert inspector.get_foreign_keys("jobs")[0]["referred_table"] == "source_tenants"
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
