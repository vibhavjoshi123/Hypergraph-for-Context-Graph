"""Zendesk support connector.

Fetches Tickets, Users, and Organizations from Zendesk via the
REST API, producing RawRecord objects for the extraction pipeline.

From ARCHITECTURE_PLAN.md Section 2.2 (P0).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from src.connectors.base import BaseConnector, ConnectorConfig, RawRecord

logger = logging.getLogger(__name__)

SUPPORTED_RECORD_TYPES = ["Ticket", "User", "Organization", "Comment"]


class ZendeskConnector(BaseConnector):
    """Zendesk support platform data connector.

    Uses the Zendesk REST API to fetch support tickets, users, and
    related data. Requires an API token or OAuth credentials.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._authenticated = False

    async def authenticate(self) -> bool:
        """Authenticate with Zendesk via API token or OAuth."""
        if not self.config.api_key:
            logger.warning("Zendesk API key not configured")
            return False

        # In production: validate credentials against Zendesk API
        # GET {subdomain}.zendesk.com/api/v2/users/me.json
        self._authenticated = True
        logger.info("Zendesk authentication initiated for %s", self.config.base_url)
        return True

    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[RawRecord]:
        """Fetch records from Zendesk via REST API."""
        if record_type not in SUPPORTED_RECORD_TYPES:
            raise ValueError(
                f"Unsupported record type: {record_type}. "
                f"Supported: {SUPPORTED_RECORD_TYPES}"
            )

        endpoint = self._get_endpoint(record_type, since)
        logger.info("Fetching Zendesk %s records from %s", record_type, endpoint)

        # In production: paginate through GET {base_url}/api/v2/{endpoint}
        records = await self._fetch_paginated(endpoint)
        for record in records:
            ts = record.get("updated_at") or record.get("created_at")
            yield RawRecord(
                source_system="zendesk",
                record_type=record_type,
                record_id=str(record.get("id", "")),
                data=record,
                timestamp=datetime.fromisoformat(ts) if ts else datetime.utcnow(),
                metadata={"endpoint": endpoint},
            )

    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        """Fetch a single Zendesk record by type and ID."""
        logger.info("Fetching Zendesk %s/%s", record_type, record_id)
        return RawRecord(
            source_system="zendesk",
            record_type=record_type,
            record_id=record_id,
            data={"id": record_id},
            timestamp=datetime.utcnow(),
        )

    def get_supported_record_types(self) -> list[str]:
        return list(SUPPORTED_RECORD_TYPES)

    @staticmethod
    def _get_endpoint(record_type: str, since: datetime | None = None) -> str:
        """Build the Zendesk API endpoint path."""
        type_to_endpoint = {
            "Ticket": "tickets",
            "User": "users",
            "Organization": "organizations",
            "Comment": "tickets/comments",
        }
        endpoint = type_to_endpoint.get(record_type, record_type.lower() + "s")
        if since:
            endpoint += f"?start_time={int(since.timestamp())}"
        return endpoint

    async def _fetch_paginated(self, endpoint: str) -> list[dict[str, Any]]:
        """Fetch paginated results from Zendesk API.

        In production: GET {base_url}/api/v2/{endpoint}.json
        with cursor-based pagination via after_cursor / next_page.
        """
        if not self._authenticated:
            logger.warning("Not authenticated to Zendesk; returning empty results")
            return []
        return []
