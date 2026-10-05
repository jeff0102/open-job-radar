"""Normalize provider records into the canonical job representation."""

from uuid import UUID

from ats_scrapers import Job

from .canonical_job import CanonicalJob


def normalize_job(source_tenant_id: UUID, job: Job) -> CanonicalJob:
    """Map an ``ats-scrapers`` job into the canonical application model."""

    provider = getattr(job.ats_type, "value", job.ats_type)
    provider_job_id = job.ats_id.strip() if job.ats_id and job.ats_id.strip() else None
    provider_data: dict[str, object] = dict(job.raw or {})

    return CanonicalJob(
        source_tenant_id=source_tenant_id,
        provider=str(provider),
        provider_job_id=provider_job_id,
        original_url=str(job.url),
        title=job.title,
        company=job.company,
        location=job.location,
        is_remote=job.is_remote,
        description=job.description,
        application_url=str(job.apply_url) if job.apply_url is not None else None,
        provider_data=provider_data,
    )


__all__ = ["CanonicalJob", "normalize_job"]
