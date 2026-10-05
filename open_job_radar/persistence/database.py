"""SQLAlchemy engine and session-factory setup."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from open_job_radar.config import get_database_url


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create an engine using the supplied or configured database URL."""

    url = get_database_url() if database_url is None else database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the session factory bound to an existing engine."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
