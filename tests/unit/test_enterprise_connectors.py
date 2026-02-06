"""Tests for enterprise data connectors (Salesforce, Zendesk, Slack, PagerDuty, Snowflake)."""

import pytest

from src.connectors.base import ConnectorConfig
from src.connectors.pagerduty import PagerDutyConnector
from src.connectors.salesforce import SalesforceConnector
from src.connectors.slack import SlackConnector
from src.connectors.snowflake import SnowflakeConnector
from src.connectors.zendesk import ZendeskConnector


class TestSalesforceConnector:
    @pytest.fixture
    def connector(self):
        return SalesforceConnector(ConnectorConfig(name="salesforce"))

    def test_supported_types(self, connector):
        types = connector.get_supported_record_types()
        assert "Account" in types
        assert "Opportunity" in types
        assert len(types) == 5

    @pytest.mark.asyncio
    async def test_authenticate_no_credentials(self, connector):
        assert not await connector.authenticate()

    @pytest.mark.asyncio
    async def test_authenticate_with_credentials(self):
        config = ConnectorConfig(
            name="salesforce", api_key="test_key", api_secret="test_secret"
        )
        connector = SalesforceConnector(config)
        assert await connector.authenticate()

    @pytest.mark.asyncio
    async def test_fetch_unsupported_type(self, connector):
        with pytest.raises(ValueError, match="Unsupported record type"):
            async for _ in connector.fetch_records("Unsupported"):
                pass

    def test_build_soql(self):
        soql = SalesforceConnector._build_soql("Account")
        assert "SELECT" in soql
        assert "FROM Account" in soql

    def test_build_soql_with_filters(self):
        soql = SalesforceConnector._build_soql(
            "Account", filters={"Industry": "Technology"}
        )
        assert "WHERE" in soql
        assert "Industry = 'Technology'" in soql


class TestZendeskConnector:
    @pytest.fixture
    def connector(self):
        return ZendeskConnector(ConnectorConfig(name="zendesk"))

    def test_supported_types(self, connector):
        types = connector.get_supported_record_types()
        assert "Ticket" in types
        assert "User" in types

    @pytest.mark.asyncio
    async def test_authenticate_no_key(self, connector):
        assert not await connector.authenticate()

    @pytest.mark.asyncio
    async def test_fetch_unsupported_type(self, connector):
        with pytest.raises(ValueError, match="Unsupported record type"):
            async for _ in connector.fetch_records("Unsupported"):
                pass

    def test_get_endpoint(self):
        endpoint = ZendeskConnector._get_endpoint("Ticket")
        assert endpoint == "tickets"


class TestSlackConnector:
    @pytest.fixture
    def connector(self):
        return SlackConnector(ConnectorConfig(name="slack"))

    def test_supported_types(self, connector):
        types = connector.get_supported_record_types()
        assert "Message" in types
        assert "Channel" in types

    @pytest.mark.asyncio
    async def test_authenticate_no_token(self, connector):
        assert not await connector.authenticate()

    @pytest.mark.asyncio
    async def test_fetch_unsupported_type(self, connector):
        with pytest.raises(ValueError, match="Unsupported record type"):
            async for _ in connector.fetch_records("Unsupported"):
                pass


class TestPagerDutyConnector:
    @pytest.fixture
    def connector(self):
        return PagerDutyConnector(ConnectorConfig(name="pagerduty"))

    def test_supported_types(self, connector):
        types = connector.get_supported_record_types()
        assert "Incident" in types
        assert "Service" in types

    @pytest.mark.asyncio
    async def test_authenticate_no_key(self, connector):
        assert not await connector.authenticate()

    def test_get_endpoint(self):
        assert PagerDutyConnector._get_endpoint("Incident") == "incidents"
        assert PagerDutyConnector._get_endpoint("OnCall") == "oncalls"


class TestSnowflakeConnector:
    @pytest.fixture
    def connector(self):
        return SnowflakeConnector(ConnectorConfig(name="snowflake"))

    def test_supported_types(self, connector):
        types = connector.get_supported_record_types()
        assert "Metric" in types
        assert "KPI" in types

    @pytest.mark.asyncio
    async def test_authenticate_no_credentials(self, connector):
        assert not await connector.authenticate()

    def test_build_query(self):
        sql = SnowflakeConnector._build_query("Metric")
        assert "SELECT * FROM enterprise_metrics" in sql

    @pytest.mark.asyncio
    async def test_fetch_unsupported_type(self, connector):
        with pytest.raises(ValueError, match="Unsupported record type"):
            async for _ in connector.fetch_records("Unsupported"):
                pass
