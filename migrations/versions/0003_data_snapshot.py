"""Add data snapshot table"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "data_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("portfolio", sa.Text(), nullable=True),
        sa.Column("watchlist", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("data_snapshot")
