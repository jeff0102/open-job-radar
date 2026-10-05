"""Provider-independent canonical job representation."""

from dataclasses import dataclass, field
from hashlib import sha256
from uuid import UUID


@dataclass(frozen=True)
class CanonicalJob:
    """Job data shared by ingestion providers and application services."""

    source_tenant_id: UUID
    provider: str
    provider_job_id: str | None
    original_url: str
    title: str
    company: str
    location: str | None = None
    is_remote: bool | None = None
    description: str | None = None
    application_url: str | None = None
    provider_data: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source_tenant_id, UUID):
            raise ValueError("source_tenant_id must be a UUID")
        if not self.provider.strip():
            raise ValueError("provider must not be blank")
        if not self.original_url.strip():
            raise ValueError("original_url must not be blank")
        if not self.title.strip():
            raise ValueError("title must not be blank")
        if not self.company.strip():
            raise ValueError("company must not be blank")
        if not isinstance(self.provider_data, dict):
            raise ValueError("provider_data must be a dictionary")


def job_identity_key(canonical_job: CanonicalJob) -> str:
    """Return a deterministic cross-provider identity for a canonical job."""

    components = (
        canonical_job.title,
        canonical_job.company,
        canonical_job.location or "",
    )
    normalized = "\x1f".join(
        " ".join(component.casefold().split()) for component in components
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


__all__ = ["CanonicalJob", "job_identity_key"]
