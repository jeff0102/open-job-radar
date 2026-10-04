# Open Job Radar — Agent Development Contract

## Project

Open Job Radar is a personal job discovery, filtering, and tracking platform.

The project aggregates jobs from ATS platforms and remote job sources, ranks them against a configurable user profile, and provides a lightweight application-tracking workflow.

## Language

All source code, comments, docstrings, documentation, commit messages, task descriptions, database identifiers, API fields, and UI copy must be written in English.

## Engineering Principles

- Prefer simple, maintainable solutions over premature abstraction.
- Reuse `ats-scrapers` instead of reimplementing ATS adapters.
- Do not modify the `ats-scrapers` dependency directly unless a concrete integration bug requires it.
- Keep provider-specific ingestion code isolated from domain logic.
- Never automate job applications. The application must link to the original job/ATS page.
- Preserve user tracking data when a source job disappears.
- Prefer deterministic rules before introducing probabilistic or LLM-based classification.
- Add tests for non-trivial business logic.
- Do not introduce microservices, Redis, Celery, Elasticsearch, React, Kubernetes, or an LLM-based ranking pipeline unless the approved project scope explicitly requires them.

## Planned Stack

- FastAPI
- Jinja2 + HTMX
- SQLAlchemy
- Alembic
- PostgreSQL (Neon)
- `ats-scrapers`
- Custom Djinni adapter
- Heroku deployment

## Autonomous Development Model

This repository is developed by an external autonomous runtime.

### Supervisor

The Supervisor:

- reads the approved project scope;
- defines the next implementation task;
- provides explicit instructions to the Executor;
- evaluates the Executor's changes;
- inspects test and validation results;
- decides whether the work is accepted, requires revision, or is blocked;
- must not modify project source code directly.

### Executor

The Executor:

- receives instructions from the Supervisor;
- inspects the repository;
- implements the requested work;
- runs tests and validation;
- may modify source code and project files;
- reports completion and encountered blockers to the runtime.

The Supervisor and Executor must use independent conversation contexts.

The Executor must not redefine requirements or expand scope on its own.

The Supervisor must not silently expand the approved scope.

## Scope Contract

The authoritative development requirements live in `SCOPE.md`.

The runtime should treat `SCOPE.md` as the source of truth for product goals, architecture, constraints, milestones, and acceptance criteria.

The Supervisor may decompose the scope into implementation tasks, but may not change the product requirements without explicit human approval.

## Autonomous Loop

The expected loop is:

1. Read the project scope and current repository state.
2. Supervisor selects the next task.
3. Executor implements that task.
4. Runtime runs deterministic validation and captures the diff.
5. Supervisor reviews the implementation and validation results.
6. If rejected, Supervisor gives concrete revision instructions.
7. Executor revises the implementation.
8. Repeat until the Supervisor accepts the task.
9. Runtime checkpoints the accepted work and proceeds to the next task.
10. Stop only when the scope is complete or the Supervisor reports a blocking issue.

The loop must have configurable iteration limits and must stop safely when limits are exceeded.

## Git Workflow

- Work on an isolated branch created by the runtime.
- Do not rewrite public history.
- Do not force-push.
- The runtime controls commits and branch checkpoints.
- The Executor should not merge branches or rewrite history.
- Pushes to the remote repository must be explicitly enabled in the runtime configuration.

## Data Safety

- Never commit secrets, API keys, local .env files, or database credentials.
- Do not log credentials or full authorization headers.
- Do not delete tracked jobs merely because an upstream source no longer returns them.
- Preserve the original application URL whenever available.

## Current Project Status

The repository is in the planning/bootstrap phase.

The autonomous runtime must not implement the full product until `SCOPE.md` has been written and accepted by the human owner.
