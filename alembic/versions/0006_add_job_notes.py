"""Add application notes to jobs.

Revision ID: 0006_job_notes
Revises: 0005_job_status
Create Date: 2026-10-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_job_notes"
down_revision: Union[str, Sequence[str], None] = "0005_job_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    notes_column = sa.Column("notes", sa.Text(), nullable=True)
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.add_column(notes_column)
    else:
        op.add_column("jobs", notes_column)


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.drop_column("notes")
    else:
        op.drop_column("jobs", "notes")
