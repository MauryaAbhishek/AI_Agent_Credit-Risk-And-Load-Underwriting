"""Create underwriting and audit tables.

Revision ID: c9ffb359c1dd
Revises: 1859a6ebee8d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9ffb359c1dd"
down_revision: Union[str, Sequence[str], None] = "1859a6ebee8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the schema for databases that don't have these tables yet."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "underwriting_records" not in existing_tables:
        op.create_table(
            "underwriting_records",
            sa.Column("application_id", sa.String(length=80), primary_key=True),
            sa.Column("applicant_reference", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("policy_version", sa.String(length=80), nullable=False),
            sa.Column("result_json", sa.JSON(), nullable=False),
        )
        op.create_index(
            "ix_underwriting_records_applicant_reference",
            "underwriting_records",
            ["applicant_reference"],
            unique=False,
        )

    if "audit_records" not in existing_tables:
        op.create_table(
            "audit_records",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("application_id", sa.String(length=80), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("policy_version", sa.String(length=80), nullable=False),
            sa.Column("details_json", sa.JSON(), nullable=False),
        )
        op.create_index(
            "ix_audit_records_application_id",
            "audit_records",
            ["application_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove tables created by this migration."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "audit_records" in existing_tables:
        op.drop_table("audit_records")

    if "underwriting_records" in existing_tables:
        op.drop_table("underwriting_records")
