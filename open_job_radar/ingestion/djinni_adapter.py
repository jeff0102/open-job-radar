"""Project-owned Djinni source-tenant adapter and payload mapping."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import UUID

from .canonical_job import CanonicalJob
from .source_tenant_adapter import SourceTenantAdapter


DjinniPayload = Mapping[str, object]


class _DjinniFetcher(Protocol):
    def fetch(self) -> Sequence[DjinniPayload]:
        """Fetch the current Djinni payloads for one configured feed."""
        ...


class DjinniFetcherFactory(Protocol):
    def __call__(self, feed_url: str, *, timeout: float) -> _DjinniFetcher:
        """Build a fetcher for one Djinni feed URL."""
        ...


@dataclass(frozen=True)
class DjinniJobRecord:
    """Provider-specific job data extracted from one Djinni payload."""

    external_id: str
    title: str
    company: str
    description: str | None
    location: str | None
    is_remote: bool | None
    original_url: str
    application_url: str | None
    provider_data: dict[str, object]


def _value(payload: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return value
    return None


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        nested = _value(value, "name", "title", "label", "text", "value")
        return _text(nested)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        parts = [part for item in value if (part := _text(item))]
        return ", ".join(parts) or None
    return str(value).strip() or None


def _remote_value(value: object | None) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.casefold().strip()
        if normalized in {"remote", "true", "yes", "1", "distributed"}:
            return True
        if normalized in {"onsite", "on-site", "office", "false", "no", "0"}:
            return False
    return None


def _external_id(payload: DjinniPayload, original_url: str | None) -> str:
    value = _text(_value(payload, "id", "job_id", "jobId", "external_id", "slug"))
    if value:
        return value
    if original_url:
        parts = [part for part in urlparse(original_url).path.split("/") if part]
        if parts:
            return parts[-1]
    raise ValueError("Djinni payload must contain a stable job id or URL.")


def parse_djinni_job(payload: DjinniPayload) -> DjinniJobRecord:
    """Parse one deterministic Djinni payload without contacting Djinni."""

    if not isinstance(payload, Mapping):
        raise TypeError("Djinni job payload must be a mapping.")

    original_url = _text(
        _value(
            payload,
            "url",
            "job_url",
            "original_url",
            "absolute_url",
            "link",
            "href",
        )
    )
    if not original_url:
        raise ValueError("Djinni payload must contain an original job URL.")

    title = _text(_value(payload, "title", "job_title", "name"))
    company = _text(_value(payload, "company", "company_name", "employer"))
    if not title:
        raise ValueError("Djinni payload must contain a job title.")
    if not company:
        raise ValueError("Djinni payload must contain a company.")

    remote = _remote_value(_value(payload, "is_remote", "remote", "remote_work"))
    if remote is None:
        remote = _remote_value(_value(payload, "workplace_type", "workplaceType"))

    return DjinniJobRecord(
        external_id=_external_id(payload, original_url),
        title=title,
        company=company,
        description=_text(_value(payload, "description", "details", "content", "body")),
        location=_text(_value(payload, "location", "locations", "region", "country")),
        is_remote=remote,
        original_url=original_url,
        application_url=_text(
            _value(payload, "application_url", "apply_url", "applyUrl", "apply_link")
        ),
        provider_data=dict(payload),
    )


def normalize_djinni_job(
    source_tenant_id: UUID, record: DjinniJobRecord
) -> CanonicalJob:
    """Map a parsed Djinni record into the provider-independent job model."""

    return CanonicalJob(
        source_tenant_id=source_tenant_id,
        provider="djinni",
        provider_job_id=record.external_id,
        original_url=record.original_url,
        title=record.title,
        company=record.company,
        location=record.location,
        is_remote=record.is_remote,
        description=record.description,
        application_url=record.application_url,
        provider_data=record.provider_data,
    )


class _UrlLibDjinniFetcher:
    def __init__(self, feed_url: str, *, timeout: float) -> None:
        self._feed_url = feed_url
        self._timeout = timeout

    def fetch(self) -> Sequence[DjinniPayload]:
        request = Request(
            self._feed_url,
            headers={"Accept": "application/json", "User-Agent": "open-job-radar"},
        )
        with urlopen(request, timeout=self._timeout) as response:
            document = json.load(response)

        if isinstance(document, list):
            return tuple(self._require_payload(item) for item in document)
        if isinstance(document, Mapping):
            records = document.get(
                "jobs", document.get("results", document.get("data"))
            )
            if isinstance(records, list):
                return tuple(self._require_payload(item) for item in records)
        raise ValueError("Djinni feed response must contain a list of job payloads.")

    @staticmethod
    def _require_payload(value: object) -> DjinniPayload:
        if not isinstance(value, Mapping):
            raise ValueError("Djinni feed contains a non-object job payload.")
        return value


class DjinniSourceTenantAdapter(SourceTenantAdapter[DjinniJobRecord]):
    """Fetch and parse jobs for one configured Djinni feed."""

    def __init__(
        self,
        source_tenant_id: UUID,
        feed_url: str,
        *,
        timeout: float = 30.0,
        fetcher_factory: DjinniFetcherFactory = _UrlLibDjinniFetcher,
    ) -> None:
        self._source_tenant_id = source_tenant_id
        self._feed_url = feed_url
        self._timeout = timeout
        self._fetcher_factory = fetcher_factory

    @property
    def source_tenant_id(self) -> UUID:
        return self._source_tenant_id

    def fetch_records(self) -> tuple[DjinniJobRecord, ...]:
        fetcher = self._fetcher_factory(self._feed_url, timeout=self._timeout)
        return tuple(parse_djinni_job(payload) for payload in fetcher.fetch())


__all__ = [
    "DjinniFetcherFactory",
    "DjinniJobRecord",
    "DjinniSourceTenantAdapter",
    "normalize_djinni_job",
    "parse_djinni_job",
]
