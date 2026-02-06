#!/usr/bin/env python3
"""Load the TypeDB schema into the database.

Usage:
    python scripts/load_schema.py [--host localhost] [--port 1729] [--database context_graph]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import TypeDBSettings
from src.typedb.client import TypeDBClient
from src.typedb.schema import SCHEMA_TYPEQL


async def main(host: str, port: int, database: str) -> None:
    """Load schema into TypeDB."""
    settings = TypeDBSettings(
        host=host,
        port=port,
        database=database,
    )

    async with TypeDBClient(settings) as client:
        if not client.is_connected:
            print(f"ERROR: Could not connect to TypeDB at {settings.address}")
            print("Make sure TypeDB is running:")
            print("  docker run -d --name typedb -p 1729:1729 typedb/typedb:latest")
            sys.exit(1)

        print(f"Connected to TypeDB at {settings.address}")

        created = await client.ensure_database()
        if created:
            print(f"Created database: {database}")
        else:
            print(f"Database already exists: {database}")

        await client.load_schema(SCHEMA_TYPEQL)
        print("Schema loaded successfully!")
        print(f"Database '{database}' is ready for use.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load TypeDB schema")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1729)
    parser.add_argument("--database", default="context_graph")
    args = parser.parse_args()

    asyncio.run(main(args.host, args.port, args.database))
