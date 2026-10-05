"""Greenhouse source-tenant adapter backed by ats-scrapers."""

from collections.abc import Callable, Sequence
from typing import Protocol
from uuid import UUID

from ats_scrapers import Job
from ats_scrapers.scrapers.greenhouse import GreenhouseScraper

from .source_tenant_adapter import SourceTenantAdapter


class _GreenhouseScraper(Protocol):
    def fetch(self) -> list[Job]:
        """Fetch the currently published jobs for a Greenhouse board."""
        ...


GreenhouseScraperFactory = Callable[..., _GreenhouseScraper]


class GreenhouseSourceTenantAdapter(SourceTenantAdapter[Job]):
    """Fetch normalized jobs for one Greenhouse company board.

    ``company_slug`` is the Greenhouse board slug used by ats-scrapers.
    Exceptions from ats-scrapers are intentionally propagated unchanged so
    callers can distinguish provider failures using its exception hierarchy.
    """

    def __init__(
        self,
        source_tenant_id: UUID,
        company_slug: str,
        *,
        timeout: float = 30.0,
        scraper_factory: GreenhouseScraperFactory = GreenhouseScraper,
    ) -> None:
        self._source_tenant_id = source_tenant_id
        self._company_slug = company_slug
        self._timeout = timeout
        self._scraper_factory = scraper_factory

    @property
    def source_tenant_id(self) -> UUID:
        return self._source_tenant_id

    def fetch_records(self) -> Sequence[Job]:
        scraper = self._scraper_factory(self._company_slug, timeout=self._timeout)
        return tuple(scraper.fetch())


__all__ = ["GreenhouseSourceTenantAdapter"]
