"""Repository operations for canonical jobs."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from open_job_radar.ingestion import CanonicalJob

from .models import Job, SourceTenant


class JobRepository:
    """Persistence operations for canonical jobs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, canonical_job: CanonicalJob) -> Job:
        """Persist one canonical job for an existing source tenant."""

        source_tenant = self._session.get(SourceTenant, canonical_job.source_tenant_id)
        if source_tenant is None:
            raise ValueError(
                f"Source tenant {canonical_job.source_tenant_id} does not exist."
            )

        job = Job(
            source_tenant=source_tenant,
            provider=canonical_job.provider,
            provider_job_id=canonical_job.provider_job_id,
            original_url=canonical_job.original_url,
            application_url=canonical_job.application_url,
            title=canonical_job.title,
            company=canonical_job.company,
            location=canonical_job.location,
            is_remote=canonical_job.is_remote,
            description=canonical_job.description,
            provider_data=canonical_job.provider_data,
        )
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def upsert(self, canonical_job: CanonicalJob) -> Job:
        """Insert or refresh a canonical job by source identity."""

        if canonical_job.provider_job_id is None:
            raise ValueError("provider_job_id is required for a canonical job upsert.")

        source_tenant = self._session.get(SourceTenant, canonical_job.source_tenant_id)
        if source_tenant is None:
            raise ValueError(
                f"Source tenant {canonical_job.source_tenant_id} does not exist."
            )

        job = self._session.scalar(
            select(Job).where(
                Job.source_tenant_id == canonical_job.source_tenant_id,
                Job.provider_job_id == canonical_job.provider_job_id,
            )
        )
        if job is None:
            job = Job(
                source_tenant=source_tenant,
                provider=canonical_job.provider,
                provider_job_id=canonical_job.provider_job_id,
                original_url=canonical_job.original_url,
                application_url=canonical_job.application_url,
                title=canonical_job.title,
                company=canonical_job.company,
                location=canonical_job.location,
                is_remote=canonical_job.is_remote,
                description=canonical_job.description,
                provider_data=canonical_job.provider_data,
            )
            self._session.add(job)
        else:
            job.original_url = canonical_job.original_url
            job.application_url = canonical_job.application_url
            job.title = canonical_job.title
            job.company = canonical_job.company
            job.location = canonical_job.location
            job.is_remote = canonical_job.is_remote
            job.description = canonical_job.description
            job.provider_data = canonical_job.provider_data

        self._session.commit()
        self._session.refresh(job)
        return job

    def get_by_id(self, job_id: UUID) -> Job | None:
        """Return the job with the given ID, if it exists."""

        return self._session.get(Job, job_id)
