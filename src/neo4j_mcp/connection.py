"""Neo4j database connection management."""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import neo4j
from neo4j import GraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError

from .config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Manages connection to Neo4j database with async support."""
    
    def __init__(self, config: Neo4jConfig):
        """Initialize the Neo4j connection.
        
        Args:
            config: Neo4j configuration object
        """
        self.config = config
        self._driver: Optional[AsyncDriver] = None
        
    async def connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                self.config.bolt_uri,
                auth=self.config.auth_tuple,
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_timeout=self.config.connection_timeout,
                encrypted=self.config.encrypted,
            )
            
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.config.bolt_uri}")
            
        except AuthError as e:
            logger.error(f"Authentication failed: {e}")
            raise ConnectionError(f"Neo4j authentication failed: {e}")
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise ConnectionError(f"Neo4j service unavailable at {self.config.bolt_uri}: {e}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    async def close(self) -> None:
        """Close the database connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._driver is not None
    
    @asynccontextmanager
    async def session(self, database: Optional[str] = None):
        """Get an async session context manager.
        
        Args:
            database: Database name, defaults to config database
            
        Yields:
            AsyncSession: Neo4j async session
        """
        if not self._driver:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")
            
        db_name = database or self.config.database
        async with self._driver.session(database=db_name) as session:
            yield session
    
    async def execute_read_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read-only Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name, defaults to config database
            
        Returns:
            List of record dictionaries
            
        Raises:
            Neo4jError: If query execution fails
        """
        if not query.strip():
            raise ValueError("Query cannot be empty")
            
        try:
            async with self.session(database) as session:
                result = await session.run(query, parameters or {})
                records = []
                async for record in result:
                    # Convert record to dictionary, handling Neo4j types
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        record_dict[key] = self._serialize_neo4j_value(value)
                    records.append(record_dict)
                
                logger.debug(f"Read query returned {len(records)} records")
                return records
                
        except Neo4jError as e:
            logger.error(f"Neo4j read query failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in read query: {e}")
            raise Neo4jError(f"Query execution failed: {e}")
    
    async def execute_write_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a write Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters  
            database: Database name, defaults to config database
            
        Returns:
            Dictionary with query summary statistics
            
        Raises:
            Neo4jError: If query execution fails
        """
        if not query.strip():
            raise ValueError("Query cannot be empty")
            
        try:
            async with self.session(database) as session:
                result = await session.run(query, parameters or {})
                summary = await result.consume()
                
                # Build summary statistics
                counters = summary.counters
                stats = {
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
                    "query_type": str(summary.query_type),
                    "result_available_after": summary.result_available_after,
                    "result_consumed_after": summary.result_consumed_after,
                }
                
                logger.debug(f"Write query completed: {stats}")
                return stats
                
        except Neo4jError as e:
            logger.error(f"Neo4j write query failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in write query: {e}")
            raise Neo4jError(f"Query execution failed: {e}")
    
    async def get_schema(self, database: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema information.
        
        Args:
            database: Database name, defaults to config database
            
        Returns:
            Dictionary containing schema information
        """
        try:
            # Get node labels and their properties
            labels_query = """
            CALL db.labels() YIELD label
            RETURN collect(label) as labels
            """
            labels_result = await self.execute_read_query(labels_query, database=database)
            labels = labels_result[0]["labels"] if labels_result else []
            
            # Get relationship types
            relationships_query = """
            CALL db.relationshipTypes() YIELD relationshipType
            RETURN collect(relationshipType) as relationshipTypes
            """
            rel_result = await self.execute_read_query(relationships_query, database=database)
            relationship_types = rel_result[0]["relationshipTypes"] if rel_result else []
            
            # Get property keys
            properties_query = """
            CALL db.propertyKeys() YIELD propertyKey
            RETURN collect(propertyKey) as propertyKeys
            """
            prop_result = await self.execute_read_query(properties_query, database=database)
            property_keys = prop_result[0]["propertyKeys"] if prop_result else []
            
            # Get constraints
            constraints_query = """
            SHOW CONSTRAINTS
            YIELD name, type, labelsOrTypes, properties
            RETURN collect({
                name: name, 
                type: type, 
                labelsOrTypes: labelsOrTypes, 
                properties: properties
            }) as constraints
            """
            try:
                constraints_result = await self.execute_read_query(constraints_query, database=database)
                constraints = constraints_result[0]["constraints"] if constraints_result else []
            except Exception:
                # Fallback for older Neo4j versions
                constraints = []
            
            # Get indexes
            indexes_query = """
            SHOW INDEXES
            YIELD name, type, labelsOrTypes, properties
            RETURN collect({
                name: name, 
                type: type, 
                labelsOrTypes: labelsOrTypes, 
                properties: properties
            }) as indexes
            """
            try:
                indexes_result = await self.execute_read_query(indexes_query, database=database)
                indexes = indexes_result[0]["indexes"] if indexes_result else []
            except Exception:
                # Fallback for older Neo4j versions
                indexes = []
            
            schema = {
                "labels": labels,
                "relationshipTypes": relationship_types,
                "propertyKeys": property_keys,
                "constraints": constraints,
                "indexes": indexes,
                "database": database or self.config.database
            }
            
            logger.debug(f"Retrieved schema for database {database or self.config.database}")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to get schema: {e}")
            raise Neo4jError(f"Failed to retrieve schema: {e}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the database connection and return server info.
        
        Returns:
            Dictionary with connection test results and server information
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            # Get server info
            server_info_query = """
            CALL dbms.components() 
            YIELD name, versions, edition
            RETURN name, versions, edition
            """
            
            async with self.session() as session:
                result = await session.run(server_info_query)
                components = []
                async for record in result:
                    components.append({
                        "name": record["name"],
                        "versions": record["versions"],
                        "edition": record["edition"]
                    })
            
            return {
                "connected": True,
                "uri": self.config.bolt_uri,
                "database": self.config.database,
                "auth_enabled": self.config.auth_tuple is not None,
                "components": components
            }
            
        except Exception as e:
            return {
                "connected": False,
                "uri": self.config.bolt_uri,
                "database": self.config.database,
                "error": str(e)
            }
    
    def _serialize_neo4j_value(self, value: Any) -> Any:
        """Convert Neo4j types to JSON-serializable values.
        
        Args:
            value: Value from Neo4j record
            
        Returns:
            JSON-serializable value
        """
        if isinstance(value, (neo4j.graph.Node, neo4j.graph.Relationship)):
            # Convert nodes and relationships to dictionaries
            result = dict(value)
            if hasattr(value, 'labels'):
                result['_labels'] = list(value.labels)
            if hasattr(value, 'type'):
                result['_type'] = value.type
            if hasattr(value, 'id'):
                result['_id'] = value.id
            if hasattr(value, 'element_id'):
                result['_element_id'] = value.element_id
            return result
        elif isinstance(value, neo4j.graph.Path):
            # Convert paths to list of nodes and relationships
            return {
                "nodes": [self._serialize_neo4j_value(node) for node in value.nodes],
                "relationships": [self._serialize_neo4j_value(rel) for rel in value.relationships]
            }
        elif isinstance(value, (list, tuple)):
            return [self._serialize_neo4j_value(item) for item in value]
        elif isinstance(value, dict):
            return {key: self._serialize_neo4j_value(val) for key, val in value.items()}
        else:
            # For basic types (str, int, float, bool, None), return as-is
            return value
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close() 