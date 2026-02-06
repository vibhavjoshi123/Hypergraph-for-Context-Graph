"""CLI entry point for the Hypergraph Context Graph."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Main CLI entry point (hcg command)."""
    parser = argparse.ArgumentParser(
        prog="hcg",
        description="Hypergraph Context Graph CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # schema subcommand
    schema_parser = subparsers.add_parser("schema", help="Print the TypeQL schema")
    schema_parser.add_argument(
        "--format", choices=["typeql", "summary"], default="typeql"
    )

    # serve subcommand
    serve_parser = subparsers.add_parser("serve", help="Start the API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command == "schema":
        from src.typedb.schema import SchemaManager

        mgr = SchemaManager()
        if args.format == "typeql":
            print(mgr.get_schema())
        else:
            print("Entity types:", mgr.get_entity_types())
            print("Relation types:", mgr.get_relation_types())

    elif args.command == "serve":
        from src.api.main import run

        run()

    else:
        parser.print_help()
        sys.exit(1)
