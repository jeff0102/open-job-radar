from dataclasses import dataclass
from uuid import UUID, uuid4

from open_job_radar.ingestion import SourceTenantAdapter


@dataclass(frozen=True)
class FakeProviderRecord:
    external_id: str


class FakeSourceTenantAdapter:
    def __init__(self, source_tenant_id: UUID) -> None:
        self._source_tenant_id = source_tenant_id

    @property
    def source_tenant_id(self) -> UUID:
        return self._source_tenant_id

    def fetch_records(self) -> tuple[FakeProviderRecord, ...]:
        return (FakeProviderRecord(external_id="job-1"),)


def test_minimal_fake_adapter_satisfies_source_tenant_contract() -> None:
    source_tenant_id = uuid4()
    adapter = FakeSourceTenantAdapter(source_tenant_id)

    assert isinstance(adapter, SourceTenantAdapter)
    assert adapter.source_tenant_id == source_tenant_id
    assert adapter.fetch_records() == (FakeProviderRecord(external_id="job-1"),)
