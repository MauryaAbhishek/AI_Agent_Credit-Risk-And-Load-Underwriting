
"""Add tamper-evident audit hashes."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7622a896cab7"
down_revision: Union[str, Sequence[str], None] = "c9ffb359c1dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hash columns without deleting existing audit records."""
    with op.batch_alter_table("audit_records") as batch_op:
        batch_op.add_column(
            sa.Column("previous_hash", sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column("event_hash", sa.String(length=64), nullable=True)
        )


def downgrade() -> None:
    """Remove hash columns."""
    with op.batch_alter_table("audit_records") as batch_op:
        batch_op.drop_column("event_hash")
        batch_op.drop_column("previous_hash")
