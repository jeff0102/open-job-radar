"""Repository operations for canonical jobs."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from open_job_radar.ingestion import CanonicalJob, job_identity_key

from .models import Job, JobStatus, SourceTenant


class JobRepository:
    """Persistence operations for canonical jobs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _validate_status(status: JobStatus | str) -> JobStatus:
        try:
            return JobStatus(status)
        except (TypeError, ValueError) as error:
            supported = ", ".join(item.value for item in JobStatus)
            raise ValueError(
                f"Invalid job status {status!r}; expected one of: {supported}."
            ) from error

    @staticmethod
    def _source_record(canonical_job: CanonicalJob) -> dict[str, object]:
        return {
            "source_tenant_id": str(canonical_job.source_tenant_id),
            "provider": canonical_job.provider,
            "provider_job_id": canonical_job.provider_job_id,
            "original_url": canonical_job.original_url,
            "application_url": canonical_job.application_url,
            "provider_data": canonical_job.provider_data,
        }

    @classmethod
    def _merge_provider_data(
        cls,
        job: Job,
        canonical_job: CanonicalJob,
    ) -> dict[str, Any]:
        existing_sources = job.provider_data.get("sources")
        if not isinstance(existing_sources, list):
            existing_sources = [
                cls._source_record(
                    CanonicalJob(
                        source_tenant_id=job.source_tenant_id,
                        provider=job.provider,
                        provider_job_id=job.provider_job_id,
                        original_url=job.original_url,
                        application_url=job.application_url,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        provider_data=job.provider_data,
                    )
                )
            ]

        source_record = cls._source_record(canonical_job)
        source_key = (
            source_record["source_tenant_id"],
            source_record["provider"],
            source_record["provider_job_id"],
        )
        sources = [
            record
            for record in existing_sources
            if not isinstance(record, dict)
            or (
                record.get("source_tenant_id"),
                record.get("provider"),
                record.get("provider_job_id"),
            )
            != source_key
        ]
        sources.append(source_record)
        return {"sources": sources}

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
            identity_key=job_identity_key(canonical_job),
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

        identity_key = job_identity_key(canonical_job)
        job = self._session.scalar(
            select(Job).where(
                Job.source_tenant_id == canonical_job.source_tenant_id,
                Job.provider_job_id == canonical_job.provider_job_id,
            )
        )
        matched_by_source = job is not None
        if job is None:
            job = self._session.scalar(
                select(Job).where(Job.identity_key == identity_key)
            )
        if job is None:
            job = Job(
                source_tenant=source_tenant,
                provider=canonical_job.provider,
                provider_job_id=canonical_job.provider_job_id,
                identity_key=identity_key,
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
            if matched_by_source:
                job.original_url = canonical_job.original_url
                job.application_url = canonical_job.application_url
                job.title = canonical_job.title
                job.company = canonical_job.company
                job.location = canonical_job.location
                job.is_remote = canonical_job.is_remote
                job.description = canonical_job.description
                if isinstance(job.provider_data.get("sources"), list):
                    job.provider_data = self._merge_provider_data(job, canonical_job)
                else:
                    job.provider_data = canonical_job.provider_data
            else:
                job.provider_data = self._merge_provider_data(job, canonical_job)

        self._session.commit()
        self._session.refresh(job)
        return job

    def list_all(self) -> list[Job]:
        """Return all persisted jobs for read-only application views."""

        statement = (
            select(Job)
            .options(joinedload(Job.source_tenant))
            .order_by(Job.created_at.desc(), Job.id)
        )
        return list(self._session.scalars(statement).all())

    def get_by_id(self, job_id: UUID) -> Job | None:
        """Return the job with the given ID, if it exists."""

        return self._session.get(Job, job_id)

    def get_status(self, job_id: UUID) -> JobStatus | None:
        """Return the application-tracking status for an existing job."""

        job = self.get_by_id(job_id)
        return None if job is None else JobStatus(job.status)

    def update_status(self, job_id: UUID, status: JobStatus | str) -> Job:
        """Set and persist a validated application-tracking status."""

        job = self.get_by_id(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} does not exist.")

        job.status = self._validate_status(status)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_notes(self, job_id: UUID) -> str | None:
        """Return application notes for an existing job."""

        job = self.get_by_id(job_id)
        return None if job is None else job.notes

    def update_notes(self, job_id: UUID, notes: str | None) -> Job:
        """Set and persist application notes for an existing job."""

        job = self.get_by_id(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} does not exist.")

        job.notes = notes
        self._session.commit()
        self._session.refresh(job)
        return job
