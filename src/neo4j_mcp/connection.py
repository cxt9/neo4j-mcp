"""Neo4j database connection — sync driver wrapped for async use."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import neo4j
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from .config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Manages a synchronous Neo4j driver, usable from async code via threads."""

    def __init__(self, config: Neo4jConfig):
        self.config = config
        self._driver: Driver | None = None
        self._connect_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    async def connect(self) -> None:
        """Establish the Neo4j driver. Idempotent and concurrency-safe."""
        if self._driver is not None:
            return
        async with self._connect_lock:
            if self._driver is not None:
                return
            self._driver = await asyncio.to_thread(self._build_driver)
            logger.info("Connected to Neo4j at %s", self.config.bolt_uri)

    def _build_driver(self) -> Driver:
        try:
            driver = GraphDatabase.driver(
                self.config.bolt_uri,
                auth=self.config.auth_tuple,
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_timeout=self.config.connection_timeout,
                encrypted=self.config.encrypted,
            )
            driver.verify_connectivity()
            return driver
        except AuthError as exc:
            raise ConnectionError(f"Neo4j authentication failed: {exc}") from exc
        except ServiceUnavailable as exc:
            raise ConnectionError(f"Neo4j service unavailable: {exc}") from exc
        except Exception as exc:
            raise ConnectionError(f"Failed to connect to Neo4j: {exc}") from exc

    async def close(self) -> None:
        if self._driver is None:
            return
        driver, self._driver = self._driver, None
        await asyncio.to_thread(driver.close)
        logger.info("Neo4j connection closed")

    def _get_driver(self) -> Driver:
        if self._driver is None:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")
        return self._driver

    def _run_query_sync(
        self,
        query: str,
        parameters: dict[str, Any] | None,
        database: str | None,
        access_mode: str,
        limit: int | None,
    ) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("Query cannot be empty")

        driver = self._get_driver()
        db = database or self.config.database

        with driver.session(database=db, default_access_mode=access_mode) as session:
            result = session.run(query, parameters or {})
            records: list[dict[str, Any]] = []
            truncated = False
            for record in result:
                if limit is not None and len(records) >= limit:
                    truncated = True
                    break
                records.append(self._serialize_value(record.data()))
            summary = result.consume()

        return {
            "records": records,
            "record_count": len(records),
            "truncated": truncated,
            "stats": self._serialize_summary(summary),
        }

    async def execute_read_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        effective_limit = limit if limit is not None else self.config.default_result_limit
        return await asyncio.to_thread(
            self._run_query_sync, query, parameters, database, neo4j.READ_ACCESS, effective_limit
        )

    async def execute_write_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        effective_limit = limit if limit is not None else self.config.default_result_limit
        return await asyncio.to_thread(
            self._run_query_sync, query, parameters, database, neo4j.WRITE_ACCESS, effective_limit
        )

    async def get_schema(self, database: str | None = None) -> dict[str, Any]:
        """Return labels, relationship types, and property keys for the database."""
        labels_q = "CALL db.labels() YIELD label RETURN collect(label) AS labels"
        rels_q = (
            "CALL db.relationshipTypes() YIELD relationshipType "
            "RETURN collect(relationshipType) AS relationshipTypes"
        )
        props_q = "CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) AS propertyKeys"

        labels = await self.execute_read_query(labels_q, database=database, limit=None)
        rels = await self.execute_read_query(rels_q, database=database, limit=None)
        props = await self.execute_read_query(props_q, database=database, limit=None)

        return {
            "database": database or self.config.database,
            "labels": labels["records"][0]["labels"] if labels["records"] else [],
            "relationshipTypes": (
                rels["records"][0]["relationshipTypes"] if rels["records"] else []
            ),
            "propertyKeys": props["records"][0]["propertyKeys"] if props["records"] else [],
        }

    async def test_connection(self) -> dict[str, Any]:
        try:
            await self.connect()
            server_info = await asyncio.to_thread(self._get_driver().get_server_info)
            return {
                "connected": True,
                "uri": self.config.bolt_uri,
                "database": self.config.database,
                "auth_enabled": self.config.auth_tuple is not None,
                "agent": server_info.agent,
                "protocol_version": str(server_info.protocol_version),
            }
        except Exception as exc:
            return {
                "connected": False,
                "uri": self.config.bolt_uri,
                "error": str(exc),
            }

    @staticmethod
    def _serialize_summary(summary: neo4j.ResultSummary) -> dict[str, Any]:
        counters = summary.counters
        return {
            "nodes_created": counters.nodes_created,
            "nodes_deleted": counters.nodes_deleted,
            "relationships_created": counters.relationships_created,
            "relationships_deleted": counters.relationships_deleted,
            "properties_set": counters.properties_set,
            "labels_added": counters.labels_added,
            "labels_removed": counters.labels_removed,
            "indexes_added": counters.indexes_added,
            "indexes_removed": counters.indexes_removed,
            "constraints_added": counters.constraints_added,
            "constraints_removed": counters.constraints_removed,
        }

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        """Recursively convert Neo4j types to JSON-serializable values."""
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, neo4j.graph.Node):
            return {
                "_type": "node",
                "_id": value.element_id,
                "_labels": sorted(value.labels),
                "_properties": {k: cls._serialize_value(v) for k, v in dict(value).items()},
            }
        if isinstance(value, neo4j.graph.Relationship):
            return {
                "_type": "relationship",
                "_id": value.element_id,
                "_rel_type": value.type,
                "_start": value.start_node.element_id if value.start_node else None,
                "_end": value.end_node.element_id if value.end_node else None,
                "_properties": {k: cls._serialize_value(v) for k, v in dict(value).items()},
            }
        if isinstance(value, neo4j.graph.Path):
            return {
                "_type": "path",
                "nodes": [cls._serialize_value(n) for n in value.nodes],
                "relationships": [cls._serialize_value(r) for r in value.relationships],
            }
        if isinstance(value, (neo4j.time.Date, neo4j.time.Time, neo4j.time.DateTime)):
            return value.iso_format()
        if isinstance(value, neo4j.time.Duration):
            return str(value)
        if isinstance(value, neo4j.spatial.Point):
            return {
                "_type": "point",
                "srid": value.srid,
                "coordinates": list(value),
            }
        if isinstance(value, (bytes, bytearray)):
            return value.hex()
        if isinstance(value, dict):
            return {k: cls._serialize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [cls._serialize_value(v) for v in value]
        return str(value)

    async def __aenter__(self) -> Neo4jConnection:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()
