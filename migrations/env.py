from __future__ import with_statement
import logging
from logging.config import fileConfig
from flask import current_app
from alembic import context

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

db = current_app.extensions["migrate"].db


def run_migrations_offline():
    url = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    context.configure(
        url=url, target_metadata=db.metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = db.engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=db.metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
