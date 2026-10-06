# Open Job Radar

A personal platform for discovering, filtering, and tracking jobs from ATS platforms and remote job sources.

## Quickstart

### Requirements

- Python 3.12 or newer (the version required by `pyproject.toml`).
- A Greenhouse board slug and Lever company slug for each source you want to sync.
- For Djinni, a URL serving a JSON feed accepted by the Djinni adapter.

Run the following commands from the repository root.

### 1. Create an environment and install the project

```sh
python -m venv .venv
```

Activate it using the command for your shell:

```powershell
.\.venv\Scripts\Activate.ps1
```

```sh
source .venv/bin/activate
```

Then install the application and its dependencies:

```sh
pip install -e .
```

### 2. Configure the database

The application and Alembic read the database connection from `DATABASE_URL`.
For a local SQLite database, set it to a file in the repository root:

```powershell
$env:DATABASE_URL = "sqlite:///./open_job_radar.db"
```

```sh
export DATABASE_URL="sqlite:///./open_job_radar.db"
```

For PostgreSQL, including Neon, use a SQLAlchemy psycopg URL and replace the
placeholders with your database values. Neon connections should use SSL:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Set that complete value as `DATABASE_URL` in your shell (with credentials
appropriate for your shell), or configure it as the `DATABASE_URL` config var
in Heroku. URL-encode special characters in the username or password.

### 3. Create the database tables

With `DATABASE_URL` set, apply all migrations:

```sh
alembic upgrade head
```

### 4. Add Greenhouse, Lever, and Djinni source tenants

The application currently creates source tenants through SQLAlchemy's
`SourceTenant` model; there is no separate tenant-creation CLI. After migration,
start an interactive Python session with `python` and paste the following code.
It creates the three tenants if a tenant with the same provider and name does
not already exist. Replace the example Greenhouse and Lever slugs and the
Djinni JSON feed URL with real values before running it.

```python
from sqlalchemy import select
from open_job_radar.persistence import (
    SourceTenant,
    create_database_engine,
    create_session_factory,
)

engine = create_database_engine()
session_factory = create_session_factory(engine)
tenants = [
    SourceTenant(
        provider="greenhouse",
        name="Example Greenhouse",
        configuration={"company_slug": "YOUR_GREENHOUSE_BOARD_SLUG"},
        enabled=True,
    ),
    SourceTenant(
        provider="lever",
        name="Example Lever",
        configuration={"company_slug": "YOUR_LEVER_COMPANY_SLUG"},
        enabled=True,
    ),
    SourceTenant(
        provider="djinni",
        name="Djinni jobs feed",
        configuration={"feed_url": "https://example.com/jobs.json"},
        enabled=True,
    ),
]
with session_factory() as session:
    for tenant in tenants:
        existing_id = session.scalar(
            select(SourceTenant.id).where(
                SourceTenant.provider == tenant.provider,
                SourceTenant.name == tenant.name,
            )
        )
        if existing_id is None:
            session.add(tenant)
    session.commit()
engine.dispose()
```

Greenhouse and Lever configurations use `company_slug`; Djinni uses `feed_url`.
The Djinni URL must return JSON containing a list of job objects (directly or
under `jobs`, `results`, or `data`), with the job fields required by the
adapter. The tenants are enabled so the synchronization command will process
them.

### 5. Synchronize jobs

Run one synchronization pass manually from the repository root:

```sh
python -m open_job_radar.scheduled_sync
```

This synchronizes each enabled source tenant once and exits with status `0` on
success or a non-zero status if synchronization fails. The command requires
`DATABASE_URL` to remain set in the process environment.

To run it automatically on Heroku, deploy the application, configure the
Heroku app's `DATABASE_URL` config var, add the Heroku Scheduler add-on, and
create a Scheduler job with the command above. Choose the desired run interval
in the Scheduler dashboard; the command is a one-shot process and Heroku
Scheduler starts it at that interval.

### 6. Start the development server

With the environment activated and `DATABASE_URL` configured, start FastAPI:

```sh
uvicorn open_job_radar.app:app --reload
```

Open <http://127.0.0.1:8000> in a browser. The health endpoint is available at
<http://127.0.0.1:8000/health>.
