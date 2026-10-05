"""Provider-independent contracts for source-tenant ingestion adapters."""

from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable
from uuid import UUID


ProviderRecordT = TypeVar("ProviderRecordT", covariant=True)


@runtime_checkable
class SourceTenantAdapter(Protocol[ProviderRecordT]):
    """Fetch provider records for one configured source tenant."""

    @property
    def source_tenant_id(self) -> UUID:
        """Return the identifier of the source tenant handled by this adapter."""
        ...

    def fetch_records(self) -> Sequence[ProviderRecordT]:
        """Return the provider records currently available for the source tenant."""
        ...
