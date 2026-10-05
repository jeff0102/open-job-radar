"""Ingestion contracts and provider adapters."""

from .greenhouse_adapter import GreenhouseSourceTenantAdapter
from .source_tenant_adapter import SourceTenantAdapter

__all__ = ["GreenhouseSourceTenantAdapter", "SourceTenantAdapter"]
