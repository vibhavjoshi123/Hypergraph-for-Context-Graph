"""Connector management API endpoints.

Provides REST endpoints for managing enterprise data connectors:
listing available connectors, checking health, and triggering syncs.

From ARCHITECTURE_PLAN.md Section 5.1.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class ConnectorStatus(BaseModel):
    """Status of an enterprise data connector."""

    name: str
    connector_type: str
    is_healthy: bool = False
    supported_record_types: list[str] = Field(default_factory=list)
    last_sync: str | None = None


class ConnectorListResponse(BaseModel):
    """Response listing all available connectors."""

    connectors: list[ConnectorStatus] = Field(default_factory=list)


class SyncRequest(BaseModel):
    """Request to trigger a connector sync."""

    connector_name: str
    record_type: str | None = None
    full_sync: bool = False


class SyncResponse(BaseModel):
    """Response from a sync operation."""

    connector_name: str
    status: str
    records_fetched: int = 0
    message: str = ""


# Available connector types for documentation
AVAILABLE_CONNECTORS = [
    ConnectorStatus(
        name="salesforce",
        connector_type="SalesforceConnector",
        supported_record_types=["Account", "Contact", "Opportunity", "Case", "Task"],
    ),
    ConnectorStatus(
        name="zendesk",
        connector_type="ZendeskConnector",
        supported_record_types=["Ticket", "User", "Organization", "Comment"],
    ),
    ConnectorStatus(
        name="slack",
        connector_type="SlackConnector",
        supported_record_types=["Message", "Channel", "Reaction", "Thread"],
    ),
    ConnectorStatus(
        name="pagerduty",
        connector_type="PagerDutyConnector",
        supported_record_types=["Incident", "Service", "OnCall", "EscalationPolicy"],
    ),
    ConnectorStatus(
        name="snowflake",
        connector_type="SnowflakeConnector",
        supported_record_types=["Metric", "UsageData", "KPI", "Report"],
    ),
    ConnectorStatus(
        name="webhook",
        connector_type="WebhookConnector",
        supported_record_types=["event"],
    ),
]


@router.get("/connectors", response_model=ConnectorListResponse)
async def list_connectors() -> ConnectorListResponse:
    """List all available enterprise data connectors and their status."""
    return ConnectorListResponse(connectors=AVAILABLE_CONNECTORS)


@router.get("/connectors/{connector_name}", response_model=ConnectorStatus)
async def get_connector(connector_name: str) -> ConnectorStatus:
    """Get status of a specific connector."""
    for connector in AVAILABLE_CONNECTORS:
        if connector.name == connector_name:
            return connector
    return ConnectorStatus(
        name=connector_name,
        connector_type="unknown",
        is_healthy=False,
    )


@router.post("/connectors/{connector_name}/health", response_model=dict[str, Any])
async def check_connector_health(connector_name: str) -> dict[str, Any]:
    """Check the health of a specific connector.

    In production, this would authenticate with the external system
    and verify connectivity.
    """
    return {
        "connector": connector_name,
        "healthy": False,
        "message": "Connector not initialized. Configure credentials in .env",
    }


@router.post("/connectors/sync", response_model=SyncResponse)
async def trigger_sync(request: SyncRequest) -> SyncResponse:
    """Trigger a data sync for a specific connector.

    In production, this would enqueue a background task to fetch
    records from the source system and process them through the
    entity extraction pipeline.
    """
    return SyncResponse(
        connector_name=request.connector_name,
        status="not_configured",
        records_fetched=0,
        message=f"Connector '{request.connector_name}' not initialized. "
                "Configure credentials in .env and restart the API.",
    )
