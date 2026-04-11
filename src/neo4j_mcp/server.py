"""Neo4j MCP server implementation using FastMCP."""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from .config import Neo4jConfig
from .connection import Neo4jConnection

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    neo4j_connection: Neo4jConnection


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    config = Neo4jConfig()
    conn = Neo4jConnection(config)
    try:
        await conn.connect()
        logger.info("Neo4j MCP server connected to %s", config.bolt_uri)
        yield AppContext(neo4j_connection=conn)
    finally:
        await conn.close()
        logger.info("Neo4j MCP server shut down")


mcp = FastMCP(name="Neo4j MCP Server", lifespan=app_lifespan)


def _conn() -> Neo4jConnection:
    ctx = mcp.get_context()
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return app_ctx.neo4j_connection


@mcp.tool()
async def cypher_query(
    query: str,
    mode: Literal["read", "write"] = "read",
    parameters: dict[str, Any] | None = None,
    database: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Execute a Cypher query against Neo4j.

    Args:
        query: The Cypher query to run.
        mode: "read" for read-only transactions, "write" for mutations. Use "write"
            for CREATE/MERGE/SET/DELETE/DROP even if the query also RETURNs rows.
        parameters: Optional parameter map. Always prefer parameters over string
            interpolation to avoid injection.
        database: Database name (defaults to the server's configured database).
        limit: Maximum rows to return. Results beyond this are dropped and
            ``truncated: true`` is set. Pass null to use the server default,
            or 0 / a large number to fetch everything.

    Returns:
        Dict with: records (list of row dicts), record_count, truncated,
        stats (write counters — all zeros for read queries).

    Examples:
        - cypher_query("MATCH (n:Person) RETURN n LIMIT 10")
        - cypher_query("CREATE (p:Person {name: $name}) RETURN p",
                       mode="write", parameters={"name": "Alice"})
    """
    try:
        if mode == "write":
            return await _conn().execute_write_query(query, parameters, database, limit)
        return await _conn().execute_read_query(query, parameters, database, limit)
    except Exception as exc:
        logger.exception("cypher_query failed")
        raise RuntimeError(f"Error executing {mode} query: {exc}") from exc


@mcp.tool()
async def get_database_schema(database: str | None = None) -> dict[str, Any]:
    """Return the labels, relationship types, and property keys for the database.

    Args:
        database: Optional database name (defaults to the configured database).
    """
    try:
        return await _conn().get_schema(database)
    except Exception as exc:
        logger.exception("get_database_schema failed")
        raise RuntimeError(f"Error retrieving schema: {exc}") from exc


@mcp.tool()
async def test_database_connection() -> dict[str, Any]:
    """Verify connectivity and return server info (agent string, protocol version)."""
    return await _conn().test_connection()


@mcp.resource("neo4j://schema")
async def schema_resource() -> str:
    try:
        schema = await _conn().get_schema()
    except Exception as exc:
        return f"Error retrieving schema: {exc}"

    labels = "\n".join(f"  - {label}" for label in sorted(schema["labels"])) or "  (none)"
    rels = "\n".join(f"  - {rt}" for rt in sorted(schema["relationshipTypes"])) or "  (none)"
    props = "\n".join(f"  - {pk}" for pk in sorted(schema["propertyKeys"])) or "  (none)"
    return (
        "Neo4j Database Schema\n"
        "=====================\n"
        f"Database: {schema['database']}\n\n"
        f"Node labels ({len(schema['labels'])}):\n{labels}\n\n"
        f"Relationship types ({len(schema['relationshipTypes'])}):\n{rels}\n\n"
        f"Property keys ({len(schema['propertyKeys'])}):\n{props}"
    )


@mcp.resource("neo4j://connection")
async def connection_resource() -> str:
    conn = _conn()
    config = conn.config
    status = await conn.test_connection()

    lines = [
        "Neo4j Connection Information",
        "============================",
        f"Bolt URI: {config.bolt_uri}",
        f"HTTP URI: {config.http_uri}",
        f"Database: {config.database}",
        f"Authentication: {'enabled' if config.auth_tuple else 'disabled'}",
        f"Encrypted: {config.encrypted}",
        f"Status: {'connected' if status['connected'] else 'disconnected'}",
    ]
    if status["connected"]:
        lines.append(f"Agent: {status.get('agent', 'unknown')}")
        lines.append(f"Protocol: {status.get('protocol_version', 'unknown')}")
    elif "error" in status:
        lines.append(f"Error: {status['error']}")
    return "\n".join(lines)


@mcp.prompt()
async def cypher_query_help() -> str:
    """Cypher syntax reference and common patterns."""
    return """\
# Cypher Query Help

## Reading data
```cypher
MATCH (n:Person) RETURN n LIMIT 10
MATCH (p:Person {name: $name})-[:KNOWS]->(friend) RETURN friend.name
```

## Writing data
```cypher
CREATE (p:Person {name: $name, age: $age}) RETURN p
MATCH (p:Person {name: $name}) SET p.age = $age
MATCH (p:Person {name: $name}) DETACH DELETE p
```

## Schema introspection
```cypher
CALL db.labels()
CALL db.relationshipTypes()
CALL db.propertyKeys()
SHOW CONSTRAINTS
SHOW INDEXES
```

## Best practices
1. Always use parameters ($name) instead of string interpolation.
2. Include LIMIT on exploratory reads.
3. Use DETACH DELETE when removing nodes with relationships.
4. Use EXPLAIN / PROFILE to inspect query plans.
"""


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Neo4j MCP Server")
    parser.add_argument(
        "--transport", choices=["stdio", "sse"], default="stdio",
        help="Transport mechanism (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=3000, help="Port for SSE transport")
    parser.add_argument("--host", default="localhost", help="Host for SSE transport")
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    try:
        if args.transport == "sse":
            logger.info("Starting Neo4j MCP server on %s:%s (SSE)", args.host, args.port)
            mcp.run(transport="sse", port=args.port, host=args.host)
        else:
            logger.info("Starting Neo4j MCP server (stdio)")
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as exc:
        logger.exception("Server error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
