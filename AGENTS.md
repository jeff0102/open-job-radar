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

## Modular Development Principles

The product must be developed as a sequence of small, atomic, independently verifiable feature increments.

A feature increment should:

- have one clear responsibility;
- touch the smallest reasonable set of modules;
- have explicit acceptance criteria;
- include focused unit tests;
- add integration tests only where a module boundary or external dependency requires them;
- be independently reviewable;
- avoid unrelated refactors;
- avoid speculative abstractions;
- leave the repository in a runnable state.

Prefer vertical slices when practical: a small feature should travel through the necessary boundaries end-to-end rather than building large incomplete layers in advance.

Separate stable domain logic from infrastructure adapters so bugs can be reproduced and tested without calling external services.

When a change is too large to review or verify confidently, the Supervisor must split it into smaller increments before assigning it.

Do not combine a feature implementation, unrelated refactor, dependency migration, and architectural cleanup in the same increment unless the dependency is necessary for the feature.

## Bug Isolation Principles

Design modules so failures can be localized.

Examples:

- ATS transport failures should be testable without the ranking system.
- Parsing failures should be testable without PostgreSQL.
- Ranking rules should be testable using fixture jobs without network access.
- Database repositories should be testable independently from the web UI.
- UI behavior should not require live ATS services.
- External integrations should be wrapped behind narrow interfaces.

Prefer deterministic fixtures and contract tests for provider integrations.

When a bug is found, reproduce it with the smallest possible test case before changing unrelated code.

## Autonomous Development Model

This repository is developed by an external autonomous runtime.

### Supervisor

The Supervisor:

- reads the approved project scope;
- defines the next atomic implementation task;
- provides explicit instructions to the Executor;
- evaluates the Executor's changes;
- inspects test and validation results;
- decides whether the work is accepted, requires revision, or is blocked;
- reviews runtime-managed conflict resolution and the merged result before accepting;
- must not modify project source code directly;
- must reject unrelated changes or scope creep.

### Executor

The Executor:

- receives instructions from the Supervisor;
- inspects the repository;
- implements only the requested atomic task;
- runs tests and validation;
- may modify source code and project files;
- reports completion, changed files, tests, and blockers to the runtime.

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
2. Supervisor identifies the smallest coherent next task.
3. Executor implements that task.
4. Runtime runs deterministic validation and captures the diff.
5. Supervisor reviews the implementation, tests, and scope compliance.
6. If rejected, Supervisor gives concrete revision instructions limited to the task.
7. Executor revises the implementation.
8. Repeat until the Supervisor accepts the task.
9. Runtime checkpoints the accepted work.
10. Supervisor selects the next atomic task.
11. Continue until the scope is complete or the Supervisor reports a blocking issue.

The loop must have configurable iteration limits and must stop safely when limits are exceeded.

## Task Sizing Rules

The Supervisor should prefer tasks that can normally be completed and validated in one focused iteration.

Examples of good atomic tasks:

- add one domain value object;
- add one repository method plus tests;
- add one database table and migration;
- add one ATS adapter contract test;
- add one scoring rule group;
- add one UI endpoint and template.

Examples of tasks that should normally be split:

- implement the entire persistence layer;
- implement all ATS integrations;
- implement the complete web UI;
- refactor the entire codebase;
- add several unrelated features at once.

## Git Workflow

- Work on the isolated session branch created by the runtime. The Executor must not switch to the target branch, merge branches, push commits, or rewrite history.
- The runtime owns Git synchronization, merge commits, checkpoints, and remote pushes.
- Remote publication is disabled unless the runtime is explicitly started with `--enable-push`.
- When remote publication is enabled, the runtime fetches the configured remote target branch and merges it into the isolated session branch before execution. If this produces conflicts, the Executor must resolve them in the working tree, preserve valid behavior from both sides, stage resolved paths with `git add`, and leave commit creation to the runtime.
- After conflict resolution, the runtime runs deterministic validation and asks the Supervisor to review the merged result. The Supervisor must not accept while Git reports unresolved conflicts. Once accepted, the runtime finalizes the merge as part of the checkpoint commit.
- After the Supervisor accepts and validation passes, the runtime checkpoints the work and pushes the session branch to the configured target with a normal fast-forward push.
- If the remote target advances during a push, the runtime synchronizes the new target and repeats Executor resolution, validation, and Supervisor review before retrying.
- Never rewrite public history or force-push. If authentication, branch protection, network failure, or an unresolved conflict prevents a safe push, preserve the local checkpoint and report the session as blocked.

## Data Safety

- Never commit secrets, API keys, local .env files, or database credentials.
- Do not log credentials or full authorization headers.
- Do not delete tracked jobs merely because an upstream source no longer returns them.
- Preserve the original application URL whenever available.

## Current Project Status

Milestone 1 — Bootstrap is complete: the application package, FastAPI health endpoint, and test foundation are present, and the focused health test passes. The next planned milestone is Milestone 2 — Persistence.

This is a progress marker, not a replacement for `SCOPE.md`. Before every new plan, the Supervisor must compare the milestone acceptance criteria with tracked and untracked files, recent Git history, completed tasks, and the current diff. A file that already exists in the repository does not need to reappear in the current task diff. Do not repeat accepted work; when completion evidence is uncertain, assign a focused verification or gap-analysis task before implementation.
