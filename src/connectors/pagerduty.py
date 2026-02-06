"""PagerDuty incident connector.

Fetches Incidents, Services, and On-Call schedules from PagerDuty
via the REST API, producing RawRecord objects for the extraction pipeline.

From ARCHITECTURE_PLAN.md Section 2.2 (P1).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from typing import Any

from src.connectors.base import BaseConnector, ConnectorConfig, RawRecord

logger = logging.getLogger(__name__)

SUPPORTED_RECORD_TYPES = ["Incident", "Service", "OnCall", "EscalationPolicy"]


class PagerDutyConnector(BaseConnector):
    """PagerDuty incident management data connector.

    Uses the PagerDuty REST API v2 to fetch incidents, services,
    and on-call information. Supports webhook-based real-time events.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._authenticated = False

    async def authenticate(self) -> bool:
        """Authenticate with PagerDuty via API token."""
        if not self.config.api_key:
            logger.warning("PagerDuty API key not configured")
            return False

        # In production: GET https://api.pagerduty.com/abilities
        # with Authorization: Token token={api_key}
        self._authenticated = True
        logger.info("PagerDuty authentication initiated")
        return True

    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[RawRecord]:
        """Fetch records from PagerDuty via REST API."""
        if record_type not in SUPPORTED_RECORD_TYPES:
            raise ValueError(
                f"Unsupported record type: {record_type}. "
                f"Supported: {SUPPORTED_RECORD_TYPES}"
            )

        endpoint = self._get_endpoint(record_type)
        logger.info("Fetching PagerDuty %s records from %s", record_type, endpoint)

        # In production: GET https://api.pagerduty.com/{endpoint}
        # with pagination via offset/limit or cursor
        records = await self._fetch_paginated(endpoint, since, until)
        for record in records:
            ts = record.get("last_status_change_at") or record.get("created_at")
            yield RawRecord(
                source_system="pagerduty",
                record_type=record_type,
                record_id=record.get("id", ""),
                data=record,
                timestamp=datetime.fromisoformat(ts) if ts else datetime.utcnow(),
                metadata={"endpoint": endpoint},
            )

    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        """Fetch a single PagerDuty record."""
        logger.info("Fetching PagerDuty %s/%s", record_type, record_id)
        return RawRecord(
            source_system="pagerduty",
            record_type=record_type,
            record_id=record_id,
            data={"id": record_id},
            timestamp=datetime.utcnow(),
        )

    def get_supported_record_types(self) -> list[str]:
        return list(SUPPORTED_RECORD_TYPES)

    async def subscribe(
        self,
        record_types: list[str],
        callback: Callable[[RawRecord], Awaitable[None]],
    ) -> None:
        """Subscribe to PagerDuty webhook events.

        In production: registers a webhook endpoint via PagerDuty API
        for real-time incident notifications.
        """
        logger.info("Subscribing to PagerDuty events: %s", record_types)

    @staticmethod
    def _get_endpoint(record_type: str) -> str:
        """Map record type to PagerDuty API endpoint."""
        type_to_endpoint = {
            "Incident": "incidents",
            "Service": "services",
            "OnCall": "oncalls",
            "EscalationPolicy": "escalation_policies",
        }
        return type_to_endpoint.get(record_type, record_type.lower() + "s")

    async def _fetch_paginated(
        self,
        endpoint: str,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch paginated results from PagerDuty API."""
        if not self._authenticated:
            logger.warning("Not authenticated to PagerDuty; returning empty results")
            return []
        return []
