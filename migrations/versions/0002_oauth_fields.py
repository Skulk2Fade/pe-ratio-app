"""Add OAuth fields"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("oauth_provider", sa.String(length=50), nullable=True))
    op.add_column("user", sa.Column("oauth_id", sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column("user", "oauth_id")
    op.drop_column("user", "oauth_provider")
