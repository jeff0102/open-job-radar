"""Lever source-tenant adapter backed by ats-scrapers."""

from collections.abc import Callable, Sequence
from typing import Protocol
from uuid import UUID

from ats_scrapers import Job
from ats_scrapers.scrapers.lever import LeverScraper

from .source_tenant_adapter import SourceTenantAdapter


class _LeverScraper(Protocol):
    def fetch(self) -> list[Job]:
        """Fetch the currently published jobs for a Lever company."""
        ...


LeverScraperFactory = Callable[..., _LeverScraper]


class LeverSourceTenantAdapter(SourceTenantAdapter[Job]):
    """Fetch normalized jobs for one Lever company board.

    ``company_slug`` is the Lever company slug used by ats-scrapers.
    Exceptions from ats-scrapers are intentionally propagated unchanged so
    callers can distinguish provider failures using its exception hierarchy.
    """

    def __init__(
        self,
        source_tenant_id: UUID,
        company_slug: str,
        *,
        timeout: float = 30.0,
        scraper_factory: LeverScraperFactory = LeverScraper,
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


__all__ = ["LeverSourceTenantAdapter"]
