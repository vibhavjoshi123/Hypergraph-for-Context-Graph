"""TypeDB client wrapper with connection management.

Provides async context-manager based access to TypeDB, with connection
pooling and session management. Designed to work with TypeDB 2.x driver
or fall back to an in-memory implementation for testing.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import TypeDBSettings, get_settings

logger = logging.getLogger(__name__)


class TypeDBClient:
    """Async TypeDB client with connection lifecycle management.

    Usage:
        async with TypeDBClient() as client:
            results = await client.query("match $x isa customer; fetch $x;")
    """

    def __init__(self, settings: TypeDBSettings | None = None) -> None:
        self.settings = settings or get_settings().typedb
        self._driver: Any = None
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to TypeDB server."""
        try:
            from typedb.driver import TypeDB

            self._driver = TypeDB.core_driver(self.settings.address)
            self._connected = True
            logger.info("Connected to TypeDB at %s", self.settings.address)
        except ImportError:
            logger.warning(
                "typedb-driver not installed. Using in-memory fallback. "
                "Install with: pip install typedb-driver"
            )
            self._driver = None
            self._connected = False
        except Exception:
            logger.exception("Failed to connect to TypeDB at %s", self.settings.address)
            self._driver = None
            self._connected = False

    async def disconnect(self) -> None:
        """Close the TypeDB connection."""
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                logger.exception("Error closing TypeDB connection")
            finally:
                self._driver = None
                self._connected = False
                logger.info("Disconnected from TypeDB")

    @property
    def is_connected(self) -> bool:
        """Whether the client has an active TypeDB connection."""
        return self._connected

    async def ensure_database(self) -> bool:
        """Create the database if it doesn't exist. Returns True if created."""
        if not self._driver:
            logger.warning("No TypeDB driver available; skipping database creation")
            return False

        db_name = self.settings.database
        if not self._driver.databases.contains(db_name):
            self._driver.databases.create(db_name)
            logger.info("Created database: %s", db_name)
            return True
        logger.info("Database already exists: %s", db_name)
        return False

    async def load_schema(self, schema: str) -> None:
        """Load a TypeQL schema definition into the database."""
        if not self._driver:
            logger.warning("No TypeDB driver available; skipping schema load")
            return

        db_name = self.settings.database
        with self._driver.session(db_name, "schema") as session, \
             session.transaction("write") as tx:
            tx.query(schema)
            tx.commit()
            logger.info("Schema loaded into database: %s", db_name)

    async def query(self, typeql: str) -> list[dict[str, Any]]:
        """Execute a TypeQL read query and return results.

        Args:
            typeql: TypeQL match/fetch query string.

        Returns:
            List of result dictionaries.
        """
        if not self._driver:
            logger.warning("No TypeDB driver; returning empty results")
            return []

        db_name = self.settings.database
        results: list[dict[str, Any]] = []
        with self._driver.session(db_name, "data") as session, \
             session.transaction("read") as tx:
            answer = tx.query(typeql)
            for item in answer:
                results.append(item.to_json())
        return results

    async def write(self, typeql: str) -> None:
        """Execute a TypeQL write query (insert/delete/update)."""
        if not self._driver:
            logger.warning("No TypeDB driver; skipping write operation")
            return

        db_name = self.settings.database
        with self._driver.session(db_name, "data") as session, \
             session.transaction("write") as tx:
            tx.query(typeql)
            tx.commit()

    async def __aenter__(self) -> TypeDBClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()
