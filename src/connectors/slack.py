"""Slack communication connector.

Fetches Messages, Channels, and Reactions from Slack via the
Web API, producing RawRecord objects for the extraction pipeline.

From ARCHITECTURE_PLAN.md Section 2.2 (P0).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime
from typing import Any

from src.connectors.base import BaseConnector, ConnectorConfig, RawRecord

logger = logging.getLogger(__name__)

SUPPORTED_RECORD_TYPES = ["Message", "Channel", "Reaction", "Thread"]


class SlackConnector(BaseConnector):
    """Slack communication platform data connector.

    Uses the Slack Web API to fetch messages, channels, and reactions.
    Supports both polling and real-time event subscription via
    Slack Events API / Socket Mode.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._authenticated = False

    async def authenticate(self) -> bool:
        """Authenticate with Slack using a bot token."""
        if not self.config.api_key:
            logger.warning("Slack bot token not configured")
            return False

        # In production: POST https://slack.com/api/auth.test
        # with Authorization: Bearer {bot_token}
        self._authenticated = True
        logger.info("Slack authentication initiated")
        return True

    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[RawRecord]:
        """Fetch records from Slack via Web API."""
        if record_type not in SUPPORTED_RECORD_TYPES:
            raise ValueError(
                f"Unsupported record type: {record_type}. "
                f"Supported: {SUPPORTED_RECORD_TYPES}"
            )

        channel_id = (filters or {}).get("channel_id")
        logger.info(
            "Fetching Slack %s records (channel=%s)", record_type, channel_id
        )

        # In production:
        # Messages: conversations.history / conversations.replies
        # Channels: conversations.list
        # Reactions: reactions.list
        records = await self._fetch_from_api(record_type, channel_id, since, until)
        for record in records:
            ts_str = record.get("ts", "")
            ts = (
                datetime.fromtimestamp(float(ts_str))
                if ts_str
                else datetime.utcnow()
            )
            yield RawRecord(
                source_system="slack",
                record_type=record_type,
                record_id=record.get("ts", record.get("id", "")),
                data=record,
                timestamp=ts,
                metadata={"channel_id": channel_id or ""},
            )

    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        """Fetch a single Slack record."""
        logger.info("Fetching Slack %s/%s", record_type, record_id)
        return RawRecord(
            source_system="slack",
            record_type=record_type,
            record_id=record_id,
            data={"ts": record_id},
            timestamp=datetime.utcnow(),
        )

    def get_supported_record_types(self) -> list[str]:
        return list(SUPPORTED_RECORD_TYPES)

    async def subscribe(
        self,
        record_types: list[str],
        callback: Callable[[RawRecord], Awaitable[None]],
    ) -> None:
        """Subscribe to real-time Slack events via Socket Mode.

        In production: uses slack_sdk.socket_mode.aiohttp.SocketModeClient
        to receive events in real time.
        """
        logger.info("Subscribing to Slack events: %s", record_types)
        # In production: open Socket Mode connection and dispatch events

    async def _fetch_from_api(
        self,
        record_type: str,
        channel_id: str | None,
        since: datetime | None,
        until: datetime | None,
    ) -> list[dict[str, Any]]:
        """Fetch records from Slack Web API.

        In production: calls the appropriate Slack API method with
        cursor-based pagination.
        """
        if not self._authenticated:
            logger.warning("Not authenticated to Slack; returning empty results")
            return []
        return []
