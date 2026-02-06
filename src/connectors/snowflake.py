"""Snowflake analytics connector.

Fetches usage metrics, KPIs, and analytical data from Snowflake,
producing RawRecord objects for the extraction pipeline.

From ARCHITECTURE_PLAN.md Section 2.2 (P1).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from src.connectors.base import BaseConnector, ConnectorConfig, RawRecord

logger = logging.getLogger(__name__)

SUPPORTED_RECORD_TYPES = ["Metric", "UsageData", "KPI", "Report"]


class SnowflakeConnector(BaseConnector):
    """Snowflake data warehouse connector.

    Executes SQL queries against Snowflake to retrieve analytics
    data, usage metrics, and KPIs. Requires Snowflake credentials
    (account, user, password/key) configured via ConnectorConfig.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._connection: Any = None

    async def authenticate(self) -> bool:
        """Authenticate with Snowflake using credentials."""
        if not self.config.api_key:
            logger.warning("Snowflake credentials not configured")
            return False

        # In production: use snowflake.connector.connect()
        # with account, user, password, warehouse, database, schema
        logger.info("Snowflake authentication initiated for %s", self.config.base_url)
        return True

    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[RawRecord]:
        """Fetch records from Snowflake via SQL queries."""
        if record_type not in SUPPORTED_RECORD_TYPES:
            raise ValueError(
                f"Unsupported record type: {record_type}. "
                f"Supported: {SUPPORTED_RECORD_TYPES}"
            )

        sql = self._build_query(record_type, since, until, filters)
        logger.info("Fetching Snowflake %s records: %s", record_type, sql)

        rows = await self._execute_query(sql)
        for row in rows:
            yield RawRecord(
                source_system="snowflake",
                record_type=record_type,
                record_id=str(row.get("id", row.get("metric_id", ""))),
                data=row,
                timestamp=datetime.fromisoformat(
                    row.get("updated_at", datetime.utcnow().isoformat())
                ),
                metadata={"sql": sql},
            )

    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        """Fetch a single record from Snowflake."""
        logger.info("Fetching Snowflake %s/%s", record_type, record_id)
        return RawRecord(
            source_system="snowflake",
            record_type=record_type,
            record_id=record_id,
            data={"id": record_id},
            timestamp=datetime.utcnow(),
        )

    def get_supported_record_types(self) -> list[str]:
        return list(SUPPORTED_RECORD_TYPES)

    @staticmethod
    def _build_query(
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """Build a SQL query for the given record type."""
        table_map = {
            "Metric": "enterprise_metrics",
            "UsageData": "product_usage",
            "KPI": "business_kpis",
            "Report": "executive_reports",
        }
        table = table_map.get(record_type, record_type.lower())
        query = f"SELECT * FROM {table}"

        conditions: list[str] = []
        if since:
            conditions.append(f"updated_at > '{since.isoformat()}'")
        if until:
            conditions.append(f"updated_at < '{until.isoformat()}'")
        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        return query

    async def _execute_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a SQL query against Snowflake.

        In production: uses snowflake.connector cursor to execute
        and fetch results as dictionaries.
        """
        if not self._connection:
            logger.warning("Not connected to Snowflake; returning empty results")
            return []
        return []
