"""Generic webhook connector for receiving events from any source.

Provides an HTTP endpoint that external systems can POST events to,
converting them into RawRecord format for the extraction pipeline.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from src.connectors.base import BaseConnector, ConnectorConfig, RawRecord


class WebhookConnector(BaseConnector):
    """Generic webhook connector for event ingestion."""

    def __init__(self, config: ConnectorConfig | None = None) -> None:
        super().__init__(config or ConnectorConfig(name="webhook"))
        self._buffer: list[RawRecord] = []

    async def authenticate(self) -> bool:
        return True

    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[RawRecord]:
        """Yield buffered records matching criteria."""
        for record in self._buffer:
            if record.record_type != record_type:
                continue
            if since and record.timestamp < since:
                continue
            if until and record.timestamp > until:
                continue
            yield record

    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        for record in self._buffer:
            if record.record_type == record_type and record.record_id == record_id:
                return record
        raise ValueError(f"Record not found: {record_type}/{record_id}")

    def get_supported_record_types(self) -> list[str]:
        return list({r.record_type for r in self._buffer})

    async def ingest(self, data: dict[str, Any]) -> RawRecord:
        """Ingest a webhook payload and buffer it as a RawRecord."""
        record = RawRecord(
            source_system=data.get("source", "webhook"),
            record_type=data.get("type", "event"),
            record_id=data.get("id", f"wh_{len(self._buffer)}"),
            data=data.get("data", data),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )
        self._buffer.append(record)
        return record
