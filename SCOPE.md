# Open Job Radar — Project Scope

## Purpose

Build a personal job discovery, filtering, ranking, and tracking platform focused on finding relevant international and remote opportunities directly from ATS platforms and selected job sources.

## Product Goals

- Discover jobs without relying on LinkedIn as the primary source.
- Aggregate jobs from supported ATS platforms.
- Add Djinni through a project-owned adapter.
- Normalize provider data into the application's job model.
- Filter opportunities against a configurable candidate profile.
- Rank relevant opportunities using deterministic rules first.
- Track personal application status and notes.
- Preserve original job and application URLs.
- Run as a lightweight personal application.

## Non-Goals

- Automated job applications.
- Public multi-user SaaS functionality.
- Complex distributed infrastructure.
- LLM-based ranking before deterministic filtering and scoring are validated.
- Premature search infrastructure such as Elasticsearch or a dedicated search cluster.

## Planned Technology

- Python
- FastAPI
- Jinja2
- HTMX
- SQLAlchemy
- Alembic
- PostgreSQL
- Neon
- ats-scrapers
- Custom Djinni adapter
- Heroku

## Autonomous Development

The project is implemented by the external Supervisor/Executor runtime described in AGENTS.md.

The Supervisor may decompose this scope into implementation tasks but may not change requirements without explicit human approval.

## Architecture

The initial application should remain a modular monolith.

Modules should have narrow responsibilities and explicit boundaries.

Preferred dependency direction:

```
Web/UI
  ↓
Application services
  ↓
Domain logic
  ↓
Repository interfaces
  ↓
Infrastructure implementations
```

External integrations should be isolated behind adapters.

The domain layer must not depend directly on HTTP clients, provider-specific payloads, or template rendering.

Core areas:

- source tenants
- ingestion
- jobs
- analysis and ranking
- tracking
- synchronization history
- web interface

ats-scrapers is the upstream ingestion layer for supported ATS providers.

## Atomic Feature Strategy

The complete product must be built incrementally.

Each milestone is a roadmap boundary, not a single implementation task.

The Supervisor must decompose each milestone into the smallest coherent feature increments that can be implemented and verified independently.

Each accepted increment should leave the application in a valid, runnable state.

A typical increment should follow:

```
Task
  ↓
Implementation
  ↓
Focused tests
  ↓
Deterministic validation
  ↓
Supervisor review
  ↓
Checkpoint
```

Avoid large "big bang" milestones.

Example decomposition for persistence:

1. database configuration;
2. database connection;
3. one model;
4. one migration;
5. one repository operation;
6. repository tests;
7. next model;
8. integration between the models.

Example decomposition for ingestion:

1. source-tenant contract;
2. one ATS adapter integration;
3. raw Job mapping;
4. persistence of one fetched job;
5. idempotent upsert;
6. sync-run recording;
7. error handling;
8. second ATS;
9. cross-ATS deduplication.

The exact decomposition is determined by the Supervisor after inspecting the current repository.

## Candidate Matching

The system must distinguish remote geography and authorization constraints instead of treating every Remote posting as globally accessible.

At minimum, the analysis layer should be able to represent:

- unknown remote scope
- Brazil
- LATAM
- Americas
- worldwide
- US-only
- EU-only
- onsite
- hybrid

Hard rejection rules must remain separate from positive scoring rules.

## Data Requirements

Tracked jobs must survive upstream disappearance when they are referenced by application history or other user tracking data.

Provider-specific information may be preserved as structured JSON when it does not fit the canonical job fields.

## Testing Strategy

Testing should be layered:

### Unit Tests

Pure domain logic, parsers, scoring rules, transformations, and validation.

### Contract / Adapter Tests

Provider integrations and adapter behavior using deterministic fixtures or mocked responses.

### Integration Tests

Database and application-service interactions that cross module boundaries.

### End-to-End Tests

Only for critical user flows and after the underlying modules are stable.

External APIs must not be required for the normal test suite.

## Milestones

### Milestone 1 — Bootstrap

Create the minimal application structure, configuration, health endpoint, and test foundation.

### Milestone 2 — Persistence

Add SQLAlchemy models, Alembic migrations, PostgreSQL configuration, and repository patterns.

### Milestone 3 — Ingestion Foundation

Integrate ats-scrapers, source tenant configuration, ingestion orchestration, normalization, and sync history.

### Milestone 4 — Candidate Analysis

Implement deterministic hard filters, remote-scope classification, matching signals, and versioned scoring.

### Milestone 5 — Job Tracking

Implement statuses, notes, and preservation of tracked jobs.

### Milestone 6 — Web Interface

Implement the job list, filtering, job details, scoring explanation, and application tracking workflow using Jinja2 + HTMX.

### Milestone 7 — Djinni

Add the project-owned Djinni adapter and integrate it into the ingestion contract.

### Milestone 8 — Production

Prepare Neon and Heroku configuration, scheduled synchronization, logging, health checks, and operational safeguards.

### Milestone 9 — Documentation and Quickstart Guide

Document the complete local setup in `README.md`, including system requirements and dependencies, environment variables, Alembic migrations, creation of initial Greenhouse, Lever, and Djinni source tenants, scheduled synchronization, and startup of the FastAPI web server.

## Acceptance Criteria

The project is complete only when:

- supported sources can be synchronized reliably;
- jobs are persisted and deduplicated;
- candidate filtering and ranking produce explainable results;
- remote geography is not incorrectly generalized;
- user tracking survives source changes;
- the web interface supports the intended personal workflow;
- tests cover the critical business logic;
- the application can run using the intended deployment stack.

### Milestone 9 — Documentation and Quickstart Guide

- [ ] `README.md` states the supported Python version and local dependency installation command, including `pip install -e .`.
- [ ] `README.md` documents `DATABASE_URL` configuration for local SQLite and PostgreSQL/Neon.
- [ ] `README.md` documents applying database migrations with `alembic upgrade head`.
- [ ] `README.md` describes a reproducible command or script for creating the initial Greenhouse, Lever, and Djinni source tenants.
- [ ] `README.md` documents manual or scheduled synchronization using `python -m open_job_radar.scheduled_sync` and explains how scheduled execution is configured.
- [ ] `README.md` documents starting the FastAPI development server with `uvicorn open_job_radar.app:app --reload`.
- [ ] The quickstart presents setup steps in an executable order and uses environment variable names and commands that match the implementation.

## Human Approval Boundary

Changes to product goals, architecture boundaries, planned technology, security model, or scope require explicit human approval.

The Supervisor may optimize task decomposition and implementation order, but may not change this product contract without human approval.
