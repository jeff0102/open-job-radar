"""FastAPI application factory for Open Job Radar."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
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


@dataclass(frozen=True, slots=True)
class JobDetailsAnalysis:
    """Score and human-readable explanations prepared for the details view."""

    score: Any | None
    explanations: tuple[str, ...]


def _string_explanations(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _signal_explanations(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()

    explanations = []
    for signal in value:
        if not isinstance(signal, Mapping):
            continue
        name = signal.get("name")
        reason = signal.get("reason")
        if (
            isinstance(name, str)
            and name.strip()
            and isinstance(reason, str)
            and reason.strip()
        ):
            explanations.append(f"{name}: {reason}")
    return tuple(explanations)


def _job_details_analysis(provider_data: Mapping[str, Any]) -> JobDetailsAnalysis:
    persisted_analysis = provider_data.get("analysis")
    analysis_data = persisted_analysis if isinstance(persisted_analysis, Mapping) else {}
    if not analysis_data:
        candidate_score = provider_data.get("candidate_score")
        if isinstance(candidate_score, Mapping):
            analysis_data = candidate_score

    score = provider_data.get("score")
    if score is None:
        score = analysis_data.get("score")

    explanations = _string_explanations(analysis_data.get("explanations"))
    if not explanations:
        explanations = _signal_explanations(analysis_data.get("signals"))
    if not explanations and isinstance(persisted_analysis, str) and persisted_analysis.strip():
        explanations = (persisted_analysis,)

    return JobDetailsAnalysis(score=score, explanations=explanations)


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
        analysis = _job_details_analysis(provider_data)
        return templates.TemplateResponse(
            request=request,
            name="job_details.html",
            context={"job": job, "analysis": analysis},
        )

    return app


app = create_app()
