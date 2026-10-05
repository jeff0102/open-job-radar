"""Repository operations for synchronization runs."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from .models import SourceTenant, SyncRun


class SyncRunRepository:
    """Persistence operations for source-tenant synchronization runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        source_tenant_id: UUID,
        *,
        started_at: datetime | None = None,
    ) -> SyncRun:
        """Start and persist a synchronization run for an existing tenant."""

        source_tenant = self._session.get(SourceTenant, source_tenant_id)
        if source_tenant is None:
            raise ValueError(f"Source tenant {source_tenant_id} does not exist.")

        sync_run = SyncRun(
            source_tenant=source_tenant,
            status="running",
            started_at=started_at or datetime.now(UTC),
        )
        self._session.add(sync_run)
        self._session.commit()
        self._session.refresh(sync_run)
        return sync_run

    def update(
        self,
        sync_run_id: UUID,
        *,
        status: str,
        completed_at: datetime | None = None,
        message: str | None = None,
    ) -> SyncRun:
        """Update a run's lifecycle status and optional completion outcome."""

        sync_run = self._session.get(SyncRun, sync_run_id)
        if sync_run is None:
            raise ValueError(f"Sync run {sync_run_id} does not exist.")

        sync_run.status = status
        sync_run.completed_at = completed_at
        sync_run.message = message
        if status in {"succeeded", "completed", "failed"} and completed_at is None:
            sync_run.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(sync_run)
        return sync_run

    def get_by_id(self, sync_run_id: UUID) -> SyncRun | None:
        """Return the synchronization run with the given ID, if it exists."""

        return self._session.get(SyncRun, sync_run_id)
