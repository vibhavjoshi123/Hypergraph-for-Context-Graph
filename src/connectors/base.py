"""Abstract base connector for enterprise data sources.

All connectors implement this interface to provide a uniform way to
fetch records from external systems (Salesforce, Zendesk, Slack, etc.)
and feed them into the entity extraction pipeline.

From ARCHITECTURE_PLAN.md Section 2.3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConnectorConfig(BaseModel):
    """Configuration for a data connector."""

    name: str
    api_key: str | None = None
    api_secret: str | None = None
    base_url: str | None = None
    rate_limit_rpm: int = Field(default=60, ge=1)
    retry_attempts: int = Field(default=3, ge=0)
    batch_size: int = Field(default=100, ge=1)


class RawRecord(BaseModel):
    """Raw record from a source system.

    This is the universal format that all connectors produce.
    Records are then processed by the entity extraction pipeline.
    """

    source_system: str
    record_type: str
    record_id: str
    data: dict[str, Any]
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract base class for all enterprise data connectors.

    Subclasses must implement:
    - authenticate(): Establish connection to the source system
    - fetch_records(): Fetch records with optional filters
    - fetch_single(): Fetch a single record by ID
    - get_supported_record_types(): List available record types
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the source system."""
        ...

    @abstractmethod
    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[RawRecord]:
        """Fetch records from the source system.

        Args:
            record_type: Type of record to fetch.
            since: Only records modified after this time.
            until: Only records modified before this time.
            filters: Additional source-specific filters.

        Yields:
            RawRecord instances.
        """
        ...
        # Make this an async generator
        if False:  # pragma: no cover
            yield  # type: ignore[misc]

    @abstractmethod
    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        """Fetch a single record by ID."""
        ...

    @abstractmethod
    def get_supported_record_types(self) -> list[str]:
        """Return list of supported record types for this connector."""
        ...

    async def subscribe(
        self,
        record_types: list[str],
        callback: Callable[[RawRecord], Awaitable[None]],
    ) -> None:
        """Subscribe to real-time updates (webhooks/streaming).

        Default implementation raises NotImplementedError.
        Connectors with real-time support should override this.
        """
        raise NotImplementedError(
            f"Real-time subscription not supported for {self.config.name}"
        )

    async def health_check(self) -> bool:
        """Check if the connector can reach the source system."""
        try:
            return await self.authenticate()
        except Exception:
            return False
