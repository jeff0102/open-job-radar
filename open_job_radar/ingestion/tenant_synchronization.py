"""Build source-tenant adapters and run configured synchronizations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
from uuid import UUID

from .djinni_adapter import (
    DjinniFetcherFactory,
    DjinniSourceTenantAdapter,
    normalize_djinni_job,
)
from .greenhouse_adapter import GreenhouseSourceTenantAdapter
from .job_mapping import normalize_job
from .lever_adapter import LeverSourceTenantAdapter
from .source_tenant_adapter import SourceTenantAdapter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from open_job_radar.persistence import SourceTenant, SyncRun


def _setting(configuration: Mapping[str, object], *names: str) -> str | None:
    for name in names:
        value = configuration.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def create_source_tenant_adapter(
    source_tenant: SourceTenant,
    *,
    djinni_fetcher_factory: DjinniFetcherFactory | None = None,
) -> SourceTenantAdapter[Any]:
    """Create the provider adapter selected by a persisted source tenant."""

    configuration = source_tenant.configuration
    provider = source_tenant.provider.casefold().strip()
    timeout = configuration.get("timeout", 30.0)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("Source tenant timeout must be a positive number.")

    if provider == "djinni":
        feed_url = _setting(configuration, "feed_url", "url", "endpoint")
        if feed_url is None:
            raise ValueError("Djinni source tenant requires a feed_url configuration.")
        kwargs: dict[str, object] = {"timeout": float(timeout)}
        if djinni_fetcher_factory is not None:
            kwargs["fetcher_factory"] = djinni_fetcher_factory
        return DjinniSourceTenantAdapter(source_tenant.id, feed_url, **kwargs)

    if provider == "greenhouse":
        company_slug = _setting(configuration, "company_slug", "board_slug")
        if company_slug is None:
            raise ValueError(
                "Greenhouse source tenant requires a company_slug configuration."
            )
        return GreenhouseSourceTenantAdapter(
            source_tenant.id,
            company_slug,
            timeout=float(timeout),
        )

    if provider == "lever":
        company_slug = _setting(configuration, "company_slug")
        if company_slug is None:
            raise ValueError(
                "Lever source tenant requires a company_slug configuration."
            )
        return LeverSourceTenantAdapter(
            source_tenant.id,
            company_slug,
            timeout=float(timeout),
        )

    raise ValueError(f"Unsupported source tenant provider {source_tenant.provider!r}.")


def synchronize_source_tenant(
    session: Session,
    source_tenant_id: UUID,
    *,
    djinni_fetcher_factory: DjinniFetcherFactory | None = None,
) -> SyncRun:
    """Synchronize one persisted source tenant using its configured provider."""

    from open_job_radar.persistence import SourceTenantRepository

    source_tenant = SourceTenantRepository(session).get_by_id(source_tenant_id)
    if source_tenant is None:
        raise ValueError(f"Source tenant {source_tenant_id} does not exist.")

    adapter = create_source_tenant_adapter(
        source_tenant,
        djinni_fetcher_factory=djinni_fetcher_factory,
    )
    mapper = (
        normalize_djinni_job
        if source_tenant.provider.casefold().strip() == "djinni"
        else normalize_job
    )

    from .synchronization import SynchronizationService

    return SynchronizationService(session, adapter, mapper=mapper).synchronize()


__all__ = ["create_source_tenant_adapter", "synchronize_source_tenant"]
