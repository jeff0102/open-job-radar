"""Ingestion contracts, canonical mapping, and provider adapters."""

from .canonical_job import CanonicalJob
from .greenhouse_adapter import GreenhouseSourceTenantAdapter
from .job_mapping import normalize_job
from .source_tenant_adapter import SourceTenantAdapter
from .synchronization import SynchronizationService

__all__ = [
    "CanonicalJob",
    "GreenhouseSourceTenantAdapter",
    "SourceTenantAdapter",
    "SynchronizationService",
    "normalize_job",
]
