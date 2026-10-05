"""FastAPI application factory for Open Job Radar."""

from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from open_job_radar.config import get_database_url
from open_job_radar.persistence import (
    JobRepository,
    JobStatus,
    create_database_engine,
    create_session_factory,
)


SessionFactory = Callable[[], Session]
TEMPLATES_DIRECTORY = Path(__file__).parent / "templates"


def create_app(
    session_factory: SessionFactory | None = None,
    database_url: str | None = None,
) -> FastAPI:
    """Create the application with an optional persistence session factory."""

    if session_factory is None:
        configured_url = get_database_url() if database_url is None else database_url
        if configured_url:
            engine = create_database_engine(configured_url)
            session_factory = create_session_factory(engine)

    templates = Jinja2Templates(directory=str(TEMPLATES_DIRECTORY))
    app = FastAPI(title="Open Job Radar")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/jobs", response_class=HTMLResponse)
    def jobs_page(
        request: Request,
        status: str | None = Query(
            default=None,
            description="Show only jobs with this application status.",
        ),
    ) -> HTMLResponse:
        status_filter = None
        if status:
            try:
                status_filter = JobStatus(status)
            except ValueError as error:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported job status filter: {status}.",
                ) from error

        jobs = []
        if session_factory is not None:
            with session_factory() as session:
                jobs = JobRepository(session).list_all(status=status_filter)
        return templates.TemplateResponse(
            request=request,
            name="jobs.html",
            context={
                "jobs": jobs,
                "statuses": JobStatus,
                "status_filter": status_filter,
            },
        )

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    def job_details(request: Request, job_id: UUID) -> HTMLResponse:
        job = None
        if session_factory is not None:
            with session_factory() as session:
                job = JobRepository(session).get_by_id(job_id)

        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")

        provider_data = job.provider_data if isinstance(job.provider_data, dict) else {}
        return templates.TemplateResponse(
            request=request,
            name="job_details.html",
            context={
                "job": job,
                "analysis": provider_data.get("analysis"),
                "score": provider_data.get("score"),
            },
        )

    return app


app = create_app()
