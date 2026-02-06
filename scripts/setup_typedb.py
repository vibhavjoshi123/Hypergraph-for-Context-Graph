#!/usr/bin/env python3
"""TypeDB setup automation script.

Creates the database, loads the schema, and optionally seeds sample data.
Run this once after deploying TypeDB to bootstrap the hypergraph.

Usage:
    python scripts/setup_typedb.py [--seed]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("setup_typedb")


async def setup(seed: bool = False) -> None:
    """Run the full TypeDB setup sequence."""
    from src.config import get_settings
    from src.typedb.client import TypeDBClient
    from src.typedb.inference import InferenceManager
    from src.typedb.schema import SCHEMA_TYPEQL

    settings = get_settings()
    logger.info("Connecting to TypeDB at %s", settings.typedb.address)

    async with TypeDBClient(settings.typedb) as client:
        if not client.is_connected:
            logger.error(
                "Could not connect to TypeDB at %s. "
                "Ensure TypeDB is running (docker run -d --name typedb "
                "-p 1729:1729 typedb/typedb:latest)",
                settings.typedb.address,
            )
            sys.exit(1)

        # Step 1: Create database
        logger.info("Step 1/4: Creating database '%s'...", settings.typedb.database)
        created = await client.ensure_database()
        if created:
            logger.info("Database created successfully")
        else:
            logger.info("Database already exists")

        # Step 2: Load schema
        logger.info("Step 2/4: Loading TypeQL schema...")
        await client.load_schema(SCHEMA_TYPEQL)
        logger.info("Schema loaded successfully")

        # Step 3: Load inference rules
        logger.info("Step 3/4: Loading inference rules...")
        inference = InferenceManager(client)
        loaded = await inference.load_rules()
        logger.info("Loaded %d inference rule(s)", loaded)

        # Step 4: Seed data (optional)
        if seed:
            logger.info("Step 4/4: Seeding sample data...")
            await _seed_data(client)
            logger.info("Sample data seeded successfully")
        else:
            logger.info("Step 4/4: Skipping seed data (use --seed to enable)")

    logger.info("TypeDB setup complete!")


async def _seed_data(client: object) -> None:
    """Seed sample enterprise data for testing."""
    from src.models.entities import Customer, Deal, Employee, Policy, Ticket
    from src.models.hyperedges import DecisionEvent, RoleAssignment
    from src.typedb.operations import HypergraphOperations

    ops = HypergraphOperations(client)  # type: ignore[arg-type]

    entities = [
        Customer(
            entity_id="cust_001",
            entity_name="Acme Corp",
            health_score=72.0,
            tier="enterprise",
            arr=500000.0,
            source_system="salesforce",
        ),
        Employee(
            entity_id="emp_001",
            entity_name="Sarah Chen",
            department="Sales",
            role="VP",
            title="VP of Sales",
            source_system="workday",
        ),
        Deal(
            entity_id="deal_001",
            entity_name="Acme Renewal Q1",
            deal_value=500000.0,
            discount_percentage=20.0,
            stage="negotiation",
            source_system="salesforce",
        ),
        Ticket(
            entity_id="tkt_001",
            entity_name="Production Outage - Jan 2026",
            severity="SEV-1",
            status="resolved",
            source_system="zendesk",
        ),
        Policy(
            entity_id="pol_001",
            entity_name="Standard Discount Policy",
            policy_type="discount",
            max_discount=15.0,
            source_system="internal",
        ),
    ]

    for entity in entities:
        await ops.insert_entity(entity)

    decision = DecisionEvent(
        hyperedge_id="dec_001",
        decision_type="discount-approval",
        rationale=(
            "VP approved 20% discount exceeding 15% policy limit "
            "due to SEV-1 incident history and strategic account status"
        ),
        participants=[
            RoleAssignment(entity_id="cust_001", role="involved-entity"),
            RoleAssignment(entity_id="emp_001", role="decision-maker"),
            RoleAssignment(entity_id="deal_001", role="involved-entity"),
            RoleAssignment(entity_id="tkt_001", role="involved-entity"),
            RoleAssignment(entity_id="pol_001", role="involved-entity"),
        ],
    )
    await ops.insert_hyperedge(decision)
    logger.info("Seeded 5 entities and 1 decision hyperedge")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up TypeDB for Hypergraph Context Graph")
    parser.add_argument("--seed", action="store_true", help="Seed sample data")
    args = parser.parse_args()
    asyncio.run(setup(seed=args.seed))


if __name__ == "__main__":
    main()
