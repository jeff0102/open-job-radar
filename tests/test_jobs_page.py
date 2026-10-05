from uuid import uuid4

from fastapi.testclient import TestClient

from open_job_radar import create_app
from open_job_radar.ingestion import CanonicalJob
from open_job_radar.persistence import (
    Base,
    JobRepository,
    SourceTenant,
    create_database_engine,
    create_session_factory,
)


def test_jobs_page_renders_persisted_job_details(tmp_path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'jobs.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    source_tenant_id = uuid4()

    try:
        with session_factory() as session:
            session.add(
                SourceTenant(
                    id=source_tenant_id,
                    provider="greenhouse",
                    name="Acme Careers",
                )
            )
            session.commit()
            job = JobRepository(session).create(
                CanonicalJob(
                    source_tenant_id=source_tenant_id,
                    provider="greenhouse",
                    provider_job_id="12345",
                    original_url="https://boards.greenhouse.io/acme/jobs/12345",
                    title="Senior Python Engineer",
                    company="Acme",
                    location="Remote - Americas",
                    is_remote=True,
                )
            )
            JobRepository(session).create(
                CanonicalJob(
                    source_tenant_id=source_tenant_id,
                    provider="greenhouse",
                    provider_job_id="67890",
                    original_url="https://boards.greenhouse.io/acme/jobs/67890",
                    title="Product Designer",
                    company="Acme",
                    location="New York",
                )
            )
            JobRepository(session).update_status(job.id, "applied")

        response = TestClient(create_app(session_factory=session_factory)).get("/jobs")

        assert response.status_code == 200
        assert "Senior Python Engineer" in response.text
        assert "Product Designer" in response.text
        assert "Acme" in response.text
        assert "Acme Careers" in response.text
        assert "Remote - Americas" in response.text
        assert "https://boards.greenhouse.io/acme/jobs/12345" in response.text
        assert "applied" in response.text
    finally:
        engine.dispose()


def test_jobs_page_filters_by_status_and_preserves_selected_value(tmp_path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'filtered.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    source_tenant_id = uuid4()

    try:
        with session_factory() as session:
            session.add(
                SourceTenant(
                    id=source_tenant_id,
                    provider="greenhouse",
                    name="Acme Careers",
                )
            )
            session.commit()
            repository = JobRepository(session)
            applied_job = repository.create(
                CanonicalJob(
                    source_tenant_id=source_tenant_id,
                    provider="greenhouse",
                    provider_job_id="12345",
                    original_url="https://boards.greenhouse.io/acme/jobs/12345",
                    title="Senior Python Engineer",
                    company="Acme",
                )
            )
            repository.create(
                CanonicalJob(
                    source_tenant_id=source_tenant_id,
                    provider="greenhouse",
                    provider_job_id="67890",
                    original_url="https://boards.greenhouse.io/acme/jobs/67890",
                    title="Product Designer",
                    company="Acme",
                )
            )
            repository.update_status(applied_job.id, "applied")

        response = TestClient(create_app(session_factory=session_factory)).get(
            "/jobs?status=applied"
        )

        assert response.status_code == 200
        assert "Senior Python Engineer" in response.text
        assert "Product Designer" not in response.text
        assert '<option value="applied" selected>' in response.text
    finally:
        engine.dispose()


def test_jobs_page_renders_empty_state_for_empty_repository(tmp_path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'empty.db'}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    try:
        response = TestClient(create_app(session_factory=session_factory)).get("/jobs")

        assert response.status_code == 200
        assert "No jobs found." in response.text
    finally:
        engine.dispose()
