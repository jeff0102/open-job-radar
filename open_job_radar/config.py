"""Environment-driven configuration for the database connection."""

from collections.abc import Mapping
from dataclasses import dataclass
import os


DATABASE_URL_ENVIRONMENT_VARIABLE = "DATABASE_URL"


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Database connection settings without opening a database connection."""

    database_url: str | None


def load_database_config(
    environment: Mapping[str, str] | None = None,
) -> DatabaseConfig:
    """Load the database URL, returning ``None`` when it is not configured.

    The process environment is read at call time so importing this module has
    no configuration side effects and tests can provide an isolated mapping.
    """

    source = os.environ if environment is None else environment
    return DatabaseConfig(
        database_url=source.get(DATABASE_URL_ENVIRONMENT_VARIABLE),
    )


def get_database_url() -> str | None:
    """Return the configured database URL, or ``None`` when absent."""

    return load_database_config().database_url
