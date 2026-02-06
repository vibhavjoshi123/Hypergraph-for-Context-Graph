"""Tests for connector interfaces."""

from datetime import datetime

import pytest

from src.connectors.base import ConnectorConfig, RawRecord
from src.connectors.webhook import WebhookConnector


class TestConnectorConfig:
    def test_defaults(self):
        config = ConnectorConfig(name="test")
        assert config.rate_limit_rpm == 60
        assert config.retry_attempts == 3
        assert config.batch_size == 100


class TestRawRecord:
    def test_creation(self):
        record = RawRecord(
            source_system="salesforce",
            record_type="Account",
            record_id="001",
            data={"Name": "Acme Corp", "AnnualRevenue": 1000000},
            timestamp=datetime(2026, 1, 15),
        )
        assert record.source_system == "salesforce"
        assert record.data["Name"] == "Acme Corp"


class TestWebhookConnector:
    @pytest.fixture
    def connector(self):
        return WebhookConnector()

    @pytest.mark.asyncio
    async def test_authenticate(self, connector):
        assert await connector.authenticate()

    @pytest.mark.asyncio
    async def test_ingest(self, connector):
        record = await connector.ingest({
            "source": "test",
            "type": "event",
            "id": "ev_001",
            "data": {"key": "value"},
            "timestamp": "2026-01-15T00:00:00",
        })
        assert record.record_id == "ev_001"
        assert record.source_system == "test"

    @pytest.mark.asyncio
    async def test_fetch_records(self, connector):
        await connector.ingest({
            "source": "test",
            "type": "alert",
            "id": "a1",
            "data": {"severity": "high"},
            "timestamp": "2026-01-15T00:00:00",
        })
        records = []
        async for r in connector.fetch_records("alert"):
            records.append(r)
        assert len(records) == 1
        assert records[0].record_id == "a1"

    @pytest.mark.asyncio
    async def test_fetch_single(self, connector):
        await connector.ingest({
            "type": "event",
            "id": "e1",
            "data": {},
            "timestamp": "2026-01-15T00:00:00",
        })
        record = await connector.fetch_single("event", "e1")
        assert record.record_id == "e1"

    @pytest.mark.asyncio
    async def test_fetch_single_not_found(self, connector):
        with pytest.raises(ValueError):
            await connector.fetch_single("event", "nonexistent")

    def test_supported_types(self, connector):
        assert connector.get_supported_record_types() == []
