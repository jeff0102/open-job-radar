"""Add deterministic cross-provider job identity.

Revision ID: 0004_job_identity
Revises: 0003_sync_runs
Create Date: 2026-10-05

"""

from hashlib import sha256
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_job_identity"
down_revision: Union[str, Sequence[str], None] = "0003_sync_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _identity_key(title: str, company: str, location: str | None) -> str:
    normalized = "\x1f".join(
        " ".join(value.casefold().split())
        for value in (title, company, location or "")
    )
    return sha256(normalized.encode("utf-8")).hexdigest()


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("identity_key", sa.String(length=64), nullable=True),
    )
    connection = op.get_bind()
    used_keys: set[str] = set()
    rows = connection.execute(
        sa.text("SELECT id, title, company, location FROM jobs")
    ).mappings()
    for row in rows:
        identity_key = _identity_key(row["title"], row["company"], row["location"])
        if identity_key in used_keys:
            identity_key = sha256(
                f"{identity_key}:{row['id']}".encode()
            ).hexdigest()
        used_keys.add(identity_key)
        connection.execute(
            sa.text("UPDATE jobs SET identity_key = :identity_key WHERE id = :id"),
            {"identity_key": identity_key, "id": row["id"]},
        )
    if connection.dialect.name == "sqlite":
        connection.commit()
    if connection.dialect.name != "sqlite":
        op.alter_column("jobs", "identity_key", nullable=False)
    op.create_index("uq_jobs_identity_key", "jobs", ["identity_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_jobs_identity_key", table_name="jobs")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.drop_column("identity_key")
    else:
        op.drop_column("jobs", "identity_key")
