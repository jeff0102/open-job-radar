"""Ingestion contracts, canonical mapping, and provider adapters."""

from .canonical_job import CanonicalJob, job_identity_key
from .djinni_adapter import (
    DjinniJobRecord,
    DjinniSourceTenantAdapter,
    normalize_djinni_job,
    parse_djinni_job,
)
from .greenhouse_adapter import GreenhouseSourceTenantAdapter
from .job_mapping import normalize_job
from .lever_adapter import LeverSourceTenantAdapter
from .source_tenant_adapter import SourceTenantAdapter
from .synchronization import SynchronizationService
from .tenant_synchronization import (
    create_source_tenant_adapter,
    synchronize_source_tenant,
)

__all__ = [
    "CanonicalJob",
    "DjinniJobRecord",
    "DjinniSourceTenantAdapter",
    "GreenhouseSourceTenantAdapter",
    "LeverSourceTenantAdapter",
    "SourceTenantAdapter",
    "SynchronizationService",
    "create_source_tenant_adapter",
    "normalize_djinni_job",
    "normalize_job",
    "parse_djinni_job",
    "synchronize_source_tenant",
]
