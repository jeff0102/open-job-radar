"""Heroku Scheduler entrypoint for one synchronization pass."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from open_job_radar.ingestion import synchronize_source_tenant
from open_job_radar.persistence import (
    SourceTenantRepository,
    create_database_engine,
    create_session_factory,
)


SessionFactory = Callable[[], Session]


class TenantSynchronizer(Protocol):
    """Callable contract for the existing tenant synchronization flow."""

    def __call__(self, session: Session, source_tenant_id: UUID) -> object:
        ...


def run_scheduled_synchronization(
    session_factory: SessionFactory,
    *,
    synchronize_tenant: TenantSynchronizer | None = None,
) -> int:
    """Synchronize every enabled tenant once and return a process status.

    Provider and database errors are intentionally not printed because their
    messages may contain credentials or other sensitive configuration.
    """

    synchronizer = (
        synchronize_source_tenant
        if synchronize_tenant is None
        else synchronize_tenant
    )
    try:
        with session_factory() as session:
            tenants = SourceTenantRepository(session).list_enabled()
            failed = False
            for tenant in tenants:
                try:
                    synchronizer(session, tenant.id)
                except Exception:
                    failed = True
                    session.rollback()
            return 1 if failed else 0
    except Exception:
        return 1


def main() -> int:
    """Run one configured synchronization pass for Heroku Scheduler."""

    engine = None
    try:
        engine = create_database_engine()
        return run_scheduled_synchronization(create_session_factory(engine))
    except Exception:
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
