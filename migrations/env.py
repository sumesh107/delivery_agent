from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import our models to ensure they're registered
from models import Base

# This is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from environment variable or default to SQLite."""
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sessions.db")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine.
    Calls to context.execute() here emit the given string to the script output.
    """
    url = get_database_url()
    
    # Remove the 'aiosqlite' prefix for offline mode (use sync URL)
    if "aiosqlite" in url:
        url = url.replace("sqlite+aiosqlite", "sqlite")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    
    # Use environment variable if set, otherwise fall back to config file
    url = get_database_url()
    configuration["sqlalchemy.url"] = url
    
    # For SQLite, create a sync engine for migrations
    # For PostgreSQL or other async databases, you may need to adjust this
    if "aiosqlite" in url:
        # Use sync sqlite for migrations
        sync_url = url.replace("sqlite+aiosqlite", "sqlite")
        connectable = create_engine(
            sync_url,
            poolclass=pool.StaticPool,
            connect_args={"check_same_thread": False},
        )
    else:
        # Use the configured URL as-is
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
