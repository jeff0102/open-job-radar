import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from open_job_radar.config import DATABASE_URL_ENVIRONMENT_VARIABLE
from open_job_radar.persistence import create_database_engine, create_session_factory


def test_database_engine_uses_configured_database_url(monkeypatch) -> None:
    monkeypatch.setenv(
        DATABASE_URL_ENVIRONMENT_VARIABLE,
        "sqlite+pysqlite:///:memory:",
    )

    engine = create_database_engine()

    try:
        assert isinstance(engine, Engine)
        assert engine.url.drivername == "sqlite+pysqlite"
        assert engine.url.database == ":memory:"
    finally:
        engine.dispose()


def test_database_engine_accepts_neon_postgresql_configuration(monkeypatch) -> None:
    monkeypatch.setenv(
        DATABASE_URL_ENVIRONMENT_VARIABLE,
        "postgresql://db.example.neon.tech/jobs?sslmode=require",
    )

    engine = create_database_engine()

    try:
        assert engine.url.drivername == "postgresql"
        assert engine.url.host == "db.example.neon.tech"
        assert engine.url.query["sslmode"] == "require"
    finally:
        engine.dispose()


def test_database_engine_requires_database_url(monkeypatch) -> None:
    monkeypatch.delenv(DATABASE_URL_ENVIRONMENT_VARIABLE, raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        create_database_engine()


def test_session_factory_opens_a_local_sqlite_session() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            assert isinstance(session, Session)
            assert session.execute(text("select 1")).scalar_one() == 1
    finally:
        engine.dispose()
