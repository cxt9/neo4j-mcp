"""Thin CLI client for testing the Neo4j MCP server over stdio."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class Neo4jMCPClient:
    """Small helper that spawns the MCP server and talks to it via stdio."""

    def __init__(self, server_command: str = "neo4j-mcp-server", server_args: list[str] | None = None):
        self._params = StdioServerParameters(
            command=server_command, args=server_args or [], env=None
        )
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> Neo4jMCPClient:
        stack = AsyncExitStack()
        try:
            read, write = await stack.enter_async_context(stdio_client(self._params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception:
            await stack.aclose()
            raise
        self._stack = stack
        self._session = session
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("Client is not connected; use `async with Neo4jMCPClient(...)`.")
        return self._session

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = await self.session.call_tool(name, arguments)
        return result.content

    async def cypher(
        self,
        query: str,
        mode: str = "read",
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        args: dict[str, Any] = {"query": query, "mode": mode}
        if parameters:
            args["parameters"] = parameters
        return await self.call_tool("cypher_query", args)

    async def schema(self) -> Any:
        return await self.call_tool("get_database_schema", {})

    async def test_connection(self) -> Any:
        return await self.call_tool("test_database_connection", {})


async def _run_once(args: argparse.Namespace) -> int:
    async with Neo4jMCPClient(args.server_command, args.server_args) as client:
        if args.test:
            result = await client.test_connection()
        elif args.schema:
            result = await client.schema()
        elif args.query:
            mode = "write" if args.write else "read"
            result = await client.cypher(args.query, mode=mode)
        else:
            tools = await client.session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            return 0

        print(json.dumps(_to_jsonable(result), indent=2, default=str))
        return 0


def _to_jsonable(value: Any) -> Any:
    """Unwrap MCP content blocks into plain JSON for printing."""
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "text"):
        try:
            return json.loads(value.text)
        except (TypeError, ValueError):
            return value.text
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Neo4j MCP Client")
    parser.add_argument("--server-command", default="neo4j-mcp-server")
    parser.add_argument("--server-args", nargs="*")
    parser.add_argument("--query", help="Execute a single Cypher query and exit")
    parser.add_argument("--write", action="store_true", help="Run the query in write mode")
    parser.add_argument("--schema", action="store_true", help="Print the database schema")
    parser.add_argument("--test", action="store_true", help="Test the database connection")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    try:
        sys.exit(asyncio.run(_run_once(args)))
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        logger.exception("Client error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
