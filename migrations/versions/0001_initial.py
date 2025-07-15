"""Initial tables"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from stockapp.extensions import db

    bind = op.get_bind()
    db.metadata.bind = bind
    db.create_all(bind=bind)


def downgrade():
    from stockapp.extensions import db

    bind = op.get_bind()
    db.metadata.bind = bind
    db.drop_all(bind=bind)
