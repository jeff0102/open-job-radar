"""Add application-tracking status to jobs.

Revision ID: 0005_job_status
Revises: 0004_job_identity
Create Date: 2026-10-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_job_status"
down_revision: Union[str, Sequence[str], None] = "0004_job_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATUS_CHECK = (
    "status IN ('new', 'saved', 'applied', 'interview', 'offer', 'rejected', 'withdrawn')"
)


def upgrade() -> None:
    status_column = sa.Column(
        "status",
        sa.String(length=32),
        nullable=False,
        server_default="new",
    )
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.add_column(status_column)
            batch_op.create_check_constraint("ck_jobs_status", _STATUS_CHECK)
    else:
        op.add_column("jobs", status_column)
        op.create_check_constraint("ck_jobs_status", "jobs", _STATUS_CHECK)


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.drop_constraint("ck_jobs_status", type_="check")
            batch_op.drop_column("status")
    else:
        op.drop_constraint("ck_jobs_status", "jobs", type_="check")
        op.drop_column("jobs", "status")
