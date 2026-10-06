"""Application service for synchronizing one source tenant."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from .canonical_job import CanonicalJob
from .job_mapping import normalize_job
from .source_tenant_adapter import SourceTenantAdapter

if TYPE_CHECKING:
    from open_job_radar.persistence import SyncRun


ProviderRecordT = TypeVar("ProviderRecordT")
CanonicalMapper = Callable[[UUID, ProviderRecordT], CanonicalJob]

logger = logging.getLogger(__name__)


class SynchronizationService(Generic[ProviderRecordT]):
    """Fetch, normalize, and persist one source tenant's current jobs."""

    def __init__(
        self,
        session: Session,
        adapter: SourceTenantAdapter[ProviderRecordT],
        *,
        mapper: CanonicalMapper[ProviderRecordT] = normalize_job,
    ) -> None:
        self._session = session
        self._adapter = adapter
        self._mapper = mapper

    def synchronize(self) -> SyncRun:
        """Run synchronization and re-raise failures after recording them."""

        from open_job_radar.persistence import JobRepository, SyncRunRepository

        sync_runs = SyncRunRepository(self._session)
        sync_run = sync_runs.create(self._adapter.source_tenant_id)
        logger.info(
            "Synchronization started",
            extra={
                "event": "synchronization_started",
                "source_tenant_id": str(self._adapter.source_tenant_id),
                "sync_run_id": str(sync_run.id),
            },
        )
        phase = "adapter fetch"
        persisted_count = 0

        try:
            records = self._adapter.fetch_records()
            for record in records:
                phase = "canonical mapping"
                canonical_job = self._mapper(self._adapter.source_tenant_id, record)
                phase = "job persistence"
                JobRepository(self._session).upsert(canonical_job)
                persisted_count += 1
        except Exception as error:
            sync_runs.update(
                sync_run.id,
                status="failed",
                completed_at=datetime.now(UTC),
                message=(
                    f"Synchronization failed during {phase} "
                    f"({type(error).__name__})."
                ),
            )
            logger.error(
                "Synchronization failed",
                extra={
                    "event": "synchronization_failed",
                    "source_tenant_id": str(self._adapter.source_tenant_id),
                    "sync_run_id": str(sync_run.id),
                    "phase": phase,
                    "persisted_count": persisted_count,
                    "error_type": type(error).__name__,
                },
            )
            raise

        completed_sync_run = sync_runs.update(
            sync_run.id,
            status="succeeded",
            completed_at=datetime.now(UTC),
            message=f"Synchronized {persisted_count} jobs.",
        )
        logger.info(
            "Synchronization succeeded",
            extra={
                "event": "synchronization_succeeded",
                "source_tenant_id": str(self._adapter.source_tenant_id),
                "sync_run_id": str(sync_run.id),
                "persisted_count": persisted_count,
            },
        )
        return completed_sync_run


__all__ = ["SynchronizationService"]
