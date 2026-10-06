"""Repository operations for source tenants."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import SourceTenant


class SourceTenantRepository:
    """Persistence operations for configured source tenants."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, source_tenant_id: UUID) -> SourceTenant | None:
        """Return the source tenant with the given ID, if it exists."""

        return self._session.get(SourceTenant, source_tenant_id)

    def list_enabled(self) -> list[SourceTenant]:
        """Return enabled tenants in a deterministic order."""

        statement = (
            select(SourceTenant)
            .where(SourceTenant.enabled.is_(True))
            .order_by(SourceTenant.name, SourceTenant.id)
        )
        return list(self._session.scalars(statement))
