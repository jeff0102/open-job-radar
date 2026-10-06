"""Heroku Scheduler entrypoint for one synchronization pass."""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


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

    Provider and database errors are intentionally not included in log messages
    because their messages may contain credentials or other sensitive data.
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
                except Exception as error:
                    failed = True
                    session.rollback()
                    logger.error(
                        "Scheduled synchronization failed for tenant",
                        extra={
                            "event": "scheduled_synchronization_tenant_failed",
                            "source_tenant_id": str(tenant.id),
                            "error_type": type(error).__name__,
                        },
                    )
            if failed:
                logger.error(
                    "Scheduled synchronization completed with failures",
                    extra={
                        "event": "scheduled_synchronization_failed",
                    },
                )
                return 1
            logger.info(
                "Scheduled synchronization succeeded",
                extra={
                    "event": "scheduled_synchronization_succeeded",
                    "tenant_count": len(tenants),
                },
            )
            return 0
    except Exception as error:
        logger.error(
            "Scheduled synchronization could not complete",
            extra={
                "event": "scheduled_synchronization_failed",
                "error_type": type(error).__name__,
            },
        )
        return 1


def main() -> int:
    """Run one configured synchronization pass for Heroku Scheduler."""

    engine = None
    try:
        engine = create_database_engine()
        return run_scheduled_synchronization(create_session_factory(engine))
    except Exception as error:
        logger.error(
            "Scheduled synchronization entrypoint failed",
            extra={
                "event": "scheduled_synchronization_failed",
                "error_type": type(error).__name__,
            },
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
