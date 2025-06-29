"""Neo4j database connection management based on a synchronous driver."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import neo4j
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError

from .config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Manages a synchronous connection to Neo4j, usable in an async context."""

    def __init__(self, config: Neo4jConfig):
        self.config = config
        self._driver: Optional[Driver] = None

    async def connect(self) -> None:
        """Establish connection to Neo4j database using an async wrapper."""
        if self._driver:
            return

        def _connect_sync():
            try:
                auth = self.config.auth_tuple
                driver = GraphDatabase.driver(
                    self.config.bolt_uri,
                    auth=auth,
                    max_connection_lifetime=self.config.max_connection_lifetime,
                    max_connection_pool_size=self.config.max_connection_pool_size,
                    connection_timeout=self.config.connection_timeout,
                    encrypted=self.config.encrypted,
                )
                driver.verify_connectivity()
                self._driver = driver
                logger.info(f"Successfully connected to Neo4j at {self.config.bolt_uri}")
            except AuthError as e:
                logger.error(f"Authentication failed for {self.config.bolt_uri}: {e}")
                raise ConnectionError(f"Neo4j authentication failed: {e}") from e
            except ServiceUnavailable as e:
                logger.error(f"Neo4j service unavailable at {self.config.bolt_uri}: {e}")
                raise ConnectionError(f"Neo4j service unavailable: {e}") from e
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise ConnectionError(f"Failed to connect to Neo4j: {e}") from e

        await asyncio.to_thread(_connect_sync)

    async def close(self) -> None:
        """Close the database connection."""
        if self._driver:
            await asyncio.to_thread(self._driver.close)
            self._driver = None
            logger.info("Neo4j connection closed")

    def _get_driver(self) -> Driver:
        if not self._driver:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")
        return self._driver

    def _execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]],
        database: Optional[str],
        access_mode: str,
    ) -> List[Dict[str, Any]]:
        """Generic sync query execution method."""
        if not query.strip():
            raise ValueError("Query cannot be empty")
        
        driver = self._get_driver()
        db = database or self.config.database

        with driver.session(database=db, default_access_mode=access_mode) as session:
            result = session.run(query, parameters or {})
            if access_mode == neo4j.WRITE_ACCESS:
                summary = result.consume()
                return [self._serialize_summary(summary)]
            else:
                records = [self._serialize_neo4j_value(record.data()) for record in result]
                return records

    async def execute_read_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None, database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read-only query in a thread-safe manner."""
        return await asyncio.to_thread(
            self._execute_query, query, parameters, database, neo4j.READ_ACCESS
        )

    async def execute_write_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None, database: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a write query in a thread-safe manner."""
        results = await asyncio.to_thread(
            self._execute_query, query, parameters, database, neo4j.WRITE_ACCESS
        )
        return results[0] if results else {}

    async def get_schema(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema information."""
        labels_query = "CALL db.labels() YIELD label RETURN collect(label) as labels"
        rels_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as relationshipTypes"
        
        labels_result = await self.execute_read_query(labels_query, database=database)
        rels_result = await self.execute_read_query(rels_query, database=database)
        
        return {
            "labels": labels_result[0]["labels"] if labels_result else [],
            "relationshipTypes": rels_result[0]["relationshipTypes"] if rels_result else [],
            "database": database or self.config.database,
        }

    async def test_connection(self) -> Dict[str, Any]:
        """Test the database connection."""
        try:
            if not self._driver:
                await self.connect()

            def _get_server_info():
                db = self.config.database
                with self._get_driver().session(database=db) as session:
                    res = session.run("CALL dbms.components() YIELD name, versions, edition")
                    return [record.data() for record in res]

            components = await asyncio.to_thread(_get_server_info)
            return {
                "connected": True, "uri": self.config.bolt_uri, "database": self.config.database,
                "auth_enabled": self.config.auth_tuple is not None, "components": components,
            }
        except Exception as e:
            return {"connected": False, "uri": self.config.bolt_uri, "error": str(e)}

    def _serialize_summary(self, summary: neo4j.ResultSummary) -> Dict[str, Any]:
        """Convert a ResultSummary to a dictionary."""
        counters = summary.counters
        return {
            "nodes_created": counters.nodes_created,
            "nodes_deleted": counters.nodes_deleted,
            "relationships_created": counters.relationships_created,
            "relationships_deleted": counters.relationships_deleted,
            "properties_set": counters.properties_set,
            "labels_added": counters.labels_added,
            "labels_removed": counters.labels_removed,
        }

    def _serialize_neo4j_value(self, value: Any) -> Any:
        """Recursively convert Neo4j types to JSON-serializable values."""
        if isinstance(value, (neo4j.graph.Node, neo4j.graph.Relationship)):
            return dict(value)
        if isinstance(value, neo4j.graph.Path):
            return {
                "nodes": [dict(n) for n in value.nodes],
                "relationships": [dict(r) for r in value.relationships],
            }
        if isinstance(value, list):
            return [self._serialize_neo4j_value(item) for item in value]
        if isinstance(value, dict):
            return {k: self._serialize_neo4j_value(v) for k, v in value.items()}
        return value

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close() 