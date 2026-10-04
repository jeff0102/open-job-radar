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

Core areas:

- source tenants
- ingestion
- jobs
- analysis and ranking
- tracking
- synchronization history
- web interface

ats-scrapers is the upstream ingestion layer for supported ATS providers.

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

## Human Approval Boundary

Changes to product goals, architecture boundaries, planned technology, security model, or scope require explicit human approval before implementation.
