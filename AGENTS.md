# Open Job Radar — Agent Development Contract

## Project

Open Job Radar is a personal job discovery, filtering, and tracking platform.

The project aggregates jobs from ATS platforms and remote job sources, ranks them against a configurable user profile, and provides a lightweight application-tracking workflow.

## Language

All source code, comments, docstrings, documentation, commit messages, issue text, database identifiers, API fields, and UI copy must be written in English.

## Engineering Principles

- Prefer simple, maintainable solutions over premature abstraction.
- Do not introduce microservices, Redis, Celery, Elasticsearch, React, Kubernetes, or an LLM-based ranking pipeline unless the project plan explicitly requires them.
- Keep the application small enough to run comfortably as a personal project.
- Reuse `ats-scrapers` instead of reimplementing ATS adapters.
- Do not modify the `ats-scrapers` dependency directly unless a concrete integration bug requires it.
- Keep provider-specific ingestion code isolated from domain logic.
- Never automate job applications. The application must link to the original job/ATS page.
- Preserve user tracking data when a source job disappears.
- Prefer deterministic rules before introducing probabilistic or LLM-based classification.
- Add tests for non-trivial business logic.

## Current Architecture

Planned stack:

- FastAPI
- Jinja2 + HTMX
- SQLAlchemy
- Alembic
- PostgreSQL (Neon)
- `ats-scrapers`
- Custom Djinni adapter
- Heroku deployment

Core domain areas:

- source tenants
- jobs
- job analysis / ranking
- job tracking
- sync runs

## Source Integration

`ats-scrapers` returns normalized `Job` objects. Treat its model as the upstream ingestion contract.

Do not create a second ATS-specific normalized schema unless there is a demonstrated need.

The application should maintain its own source-tenant record because `Job.company` is not guaranteed to be a canonical company identity across providers.

## Filtering and Ranking

Hard rejection rules and positive ranking signals must remain separate.

Unknown remote geography must not be treated as globally remote.

The system must distinguish at least:

- unknown remote scope
- Brazil
- LATAM
- Americas
- worldwide
- US-only
- EU-only
- onsite
- hybrid

Keep ranking rules versioned so historical analysis can be recomputed without refetching jobs.

## Data Safety

- Never commit secrets, API keys, local .env files, or database credentials.
- Do not log credentials or full authorization headers.
- Do not delete tracked jobs merely because an upstream source no longer returns them.
- Preserve the original application URL whenever available.

## Development Workflow

Before implementing a new feature:

1. Inspect the existing code and related tests.
2. Check the project plan and repository issues.
3. Make the smallest coherent change.
4. Add or update tests.
5. Run the relevant test suite.
6. Summarize changes, validation, and any unresolved risks.

An agent must not make broad architectural changes based only on a single task description.

## Git Workflow

Use small, descriptive commits.

Do not rewrite public history.

Do not force-push.

Prefer working on a dedicated branch for each task.

Do not merge pull requests unless explicitly instructed.

## Autonomous Operation

The runtime repository may execute coding agents against this repository.

When an agent is operating autonomously:

- It may inspect, implement, test, and commit changes.
- It should work from explicit GitHub issues or task instructions.
- It should stop rather than inventing requirements when a task conflicts with the architecture contract.
- It should leave a concise completion summary suitable for a pull request description.

## Current Project Status

The repository is in the bootstrap phase.

Do not begin implementing the complete application until the project plan has been recorded and the repository bootstrap has been validated.
