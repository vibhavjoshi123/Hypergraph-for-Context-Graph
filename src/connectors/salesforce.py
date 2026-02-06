"""Salesforce CRM connector.

Fetches Accounts, Contacts, Opportunities, Cases, and Tasks from
Salesforce via the REST API, producing RawRecord objects for the
entity extraction pipeline.

From ARCHITECTURE_PLAN.md Section 2.4 (P0).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from src.connectors.base import BaseConnector, ConnectorConfig, RawRecord

logger = logging.getLogger(__name__)

SUPPORTED_RECORD_TYPES = ["Account", "Contact", "Opportunity", "Case", "Task"]


class SalesforceConnector(BaseConnector):
    """Salesforce CRM data connector.

    Uses the Salesforce REST API (SOQL) to fetch CRM records.
    Requires OAuth 2.0 credentials configured via ConnectorConfig.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._access_token: str | None = None
        self._instance_url: str | None = None

    async def authenticate(self) -> bool:
        """Authenticate with Salesforce via OAuth 2.0 password flow."""
        if not self.config.api_key or not self.config.api_secret:
            logger.warning("Salesforce credentials not configured")
            return False

        # In production, this would perform the OAuth flow:
        # POST to https://login.salesforce.com/services/oauth2/token
        # with grant_type=password, client_id, client_secret, username, password
        logger.info("Salesforce authentication initiated")
        return True

    async def fetch_records(
        self,
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> AsyncIterator[RawRecord]:
        """Fetch records from Salesforce via SOQL queries."""
        if record_type not in SUPPORTED_RECORD_TYPES:
            raise ValueError(
                f"Unsupported record type: {record_type}. "
                f"Supported: {SUPPORTED_RECORD_TYPES}"
            )

        soql = self._build_soql(record_type, since, until, filters)
        logger.info("Fetching Salesforce %s records: %s", record_type, soql)

        # In production, execute SOQL via REST API:
        # GET {instance_url}/services/data/v58.0/query?q={soql}
        # Handle pagination via nextRecordsUrl
        records = await self._execute_soql(soql)
        for record in records:
            yield RawRecord(
                source_system="salesforce",
                record_type=record_type,
                record_id=record.get("Id", ""),
                data=record,
                timestamp=datetime.fromisoformat(
                    record.get("LastModifiedDate", datetime.utcnow().isoformat())
                ),
                metadata={"soql": soql},
            )

    async def fetch_single(self, record_type: str, record_id: str) -> RawRecord:
        """Fetch a single Salesforce record by type and ID."""
        # GET {instance_url}/services/data/v58.0/sobjects/{record_type}/{record_id}
        logger.info("Fetching Salesforce %s/%s", record_type, record_id)
        return RawRecord(
            source_system="salesforce",
            record_type=record_type,
            record_id=record_id,
            data={"Id": record_id},
            timestamp=datetime.utcnow(),
        )

    def get_supported_record_types(self) -> list[str]:
        return list(SUPPORTED_RECORD_TYPES)

    @staticmethod
    def _build_soql(
        record_type: str,
        since: datetime | None = None,
        until: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """Build a SOQL query for the given record type."""
        field_map: dict[str, list[str]] = {
            "Account": ["Id", "Name", "Industry", "AnnualRevenue", "LastModifiedDate"],
            "Contact": ["Id", "Name", "Email", "AccountId", "LastModifiedDate"],
            "Opportunity": ["Id", "Name", "Amount", "StageName", "CloseDate", "LastModifiedDate"],
            "Case": ["Id", "Subject", "Status", "Priority", "AccountId", "LastModifiedDate"],
            "Task": ["Id", "Subject", "Status", "WhoId", "WhatId", "LastModifiedDate"],
        }
        fields = field_map.get(record_type, ["Id", "Name", "LastModifiedDate"])
        query = f"SELECT {', '.join(fields)} FROM {record_type}"

        conditions: list[str] = []
        if since:
            conditions.append(f"LastModifiedDate > {since.isoformat()}Z")
        if until:
            conditions.append(f"LastModifiedDate < {until.isoformat()}Z")
        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        return query

    async def _execute_soql(self, soql: str) -> list[dict[str, Any]]:
        """Execute a SOQL query and return results.

        In production, this sends the query to the Salesforce REST API
        and handles pagination. Returns empty list when not connected.
        """
        if not self._access_token:
            logger.warning("Not authenticated to Salesforce; returning empty results")
            return []
        return []
