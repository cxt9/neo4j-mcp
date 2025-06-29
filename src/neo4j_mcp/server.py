"""Neo4j MCP Server implementation using FastMCP."""

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, AsyncIterator

from mcp.server.fastmcp import FastMCP, Context
from neo4j.exceptions import Neo4jError

from .config import Neo4jConfig
from .connection import Neo4jConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context containing shared resources."""
    neo4j_connection: Neo4jConnection


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with Neo4j connection."""
    config = Neo4jConfig()
    neo4j_conn = Neo4jConnection(config)
    
    try:
        await neo4j_conn.connect()
        logger.info(f"Neo4j MCP Server connected to {config.bolt_uri}")
        yield AppContext(neo4j_connection=neo4j_conn)
    finally:
        await neo4j_conn.close()
        logger.info("Neo4j MCP Server shut down")


# Create FastMCP server with lifespan management
mcp = FastMCP(
    name="Neo4j MCP Server",
    description="Model Context Protocol server for Neo4j database access",
    lifespan=app_lifespan
)


def _get_neo4j_connection() -> Neo4jConnection:
    """Get the Neo4j connection from the application context."""
    ctx = mcp.get_context()
    app_context: AppContext = ctx.request_context.lifespan_context
    return app_context.neo4j_connection


@mcp.tool()
async def read_cypher_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Execute a read-only Cypher query against the Neo4j database.
    
    Args:
        query: The Cypher query to execute (should be read-only)
        parameters: Optional parameters for the Cypher query
        database: Optional database name (defaults to configured database)
    
    Returns:
        List of records as dictionaries
    
    Examples:
        - MATCH (n:Person) RETURN n LIMIT 10
        - MATCH (p:Person {name: $name})-[:KNOWS]->(friend) RETURN friend.name
        - CALL db.labels()
    """
    try:
        conn = _get_neo4j_connection()
        result = await conn.execute_read_query(query, parameters, database)
        logger.info(f"Read query executed successfully, returned {len(result)} records")
        return result
    except Exception as e:
        error_msg = f"Error executing read query: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool()
async def write_cypher_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None
) -> Dict[str, Any]:
    """Execute a write Cypher query against the Neo4j database.
    
    Args:
        query: The Cypher query to execute (CREATE, UPDATE, DELETE, etc.)
        parameters: Optional parameters for the Cypher query
        database: Optional database name (defaults to configured database)
    
    Returns:
        Dictionary containing query execution statistics
    
    Examples:
        - CREATE (p:Person {name: $name, age: $age}) RETURN p
        - MATCH (p:Person {name: $name}) SET p.age = $age
        - MATCH (p:Person {name: $name}) DELETE p
    """
    try:
        conn = _get_neo4j_connection()
        result = await conn.execute_write_query(query, parameters, database)
        logger.info(f"Write query executed successfully: {result}")
        return result
    except Exception as e:
        error_msg = f"Error executing write query: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool()
async def get_database_schema(database: Optional[str] = None) -> Dict[str, Any]:
    """Get the schema information for the Neo4j database.
    
    Args:
        database: Optional database name (defaults to configured database)
    
    Returns:
        Dictionary containing schema information including:
        - labels: List of node labels
        - relationshipTypes: List of relationship types
    """
    try:
        conn = _get_neo4j_connection()
        schema = await conn.get_schema(database)
        logger.info(f"Schema retrieved for database {database or 'default'}")
        return schema
    except Exception as e:
        error_msg = f"Error retrieving schema: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.tool()
async def test_database_connection() -> Dict[str, Any]:
    """Test the connection to the Neo4j database and return server information.
    
    Returns:
        Dictionary with connection status and server details
    """
    try:
        conn = _get_neo4j_connection()
        test_result = await conn.test_connection()
        logger.info("Database connection test completed")
        return test_result
    except Exception as e:
        error_msg = f"Error testing connection: {str(e)}"
        logger.error(error_msg)
        return {
            "connected": False,
            "error": error_msg
        }


@mcp.tool()
async def run_cypher_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None,
    read_only: bool = True
) -> Dict[str, Any]:
    """Execute a Cypher query with automatic read/write detection.
    
    Args:
        query: The Cypher query to execute
        parameters: Optional parameters for the Cypher query
        database: Optional database name (defaults to configured database)
        read_only: Whether to execute as read-only query (safer, default True)
    
    Returns:
        Dictionary containing either query results or execution statistics
    """
    try:
        conn = _get_neo4j_connection()
        
        if read_only:
            result = await conn.execute_read_query(query, parameters, database)
            return {
                "type": "read",
                "records": result,
                "count": len(result)
            }
        else:
            result = await conn.execute_write_query(query, parameters, database)
            return {
                "type": "write",
                "statistics": result
            }
    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


@mcp.resource("neo4j://schema")
async def get_schema_resource() -> str:
    """Get the Neo4j database schema as a formatted resource.
    
    Returns:
        Formatted string representation of the database schema
    """
    try:
        conn = _get_neo4j_connection()
        schema = await conn.get_schema()
        
        # Format schema for better readability
        formatted_schema = f"""
Neo4j Database Schema
=====================
Database: {schema['database']}
Node Labels ({len(schema['labels'])}):
{chr(10).join(f"  - {label}" for label in sorted(schema['labels']))}
Relationship Types ({len(schema['relationshipTypes'])}):
{chr(10).join(f"  - {rel_type}" for rel_type in sorted(schema['relationshipTypes']))}
"""
        return formatted_schema.strip()
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"


@mcp.resource("neo4j://connection")
async def get_connection_info() -> str:
    """Get Neo4j connection information as a formatted resource.
    
    Returns:
        Formatted string with connection details
    """
    try:
        conn = _get_neo4j_connection()
        config = conn.config
        test_result = await conn.test_connection()
        
        connection_info = f"""
Neo4j Connection Information
============================

Server URI: {config.bolt_uri}
HTTP URI: {config.http_uri}
Database: {config.database}
Authentication: {"Enabled" if config.auth_tuple else "Disabled"}
Encrypted: {config.encrypted}

Connection Status: {"✓ Connected" if test_result['connected'] else "✗ Disconnected"}

"""
        if test_result['connected'] and 'components' in test_result:
            connection_info += "Server Components:\n"
            for component in test_result['components']:
                connection_info += f"  - {component['name']}: {', '.join(component['versions'])} ({component['edition']})\n"
        
        if not test_result['connected'] and 'error' in test_result:
            connection_info += f"Error: {test_result['error']}\n"
            
        return connection_info.strip()
    except Exception as e:
        return f"Error retrieving connection info: {str(e)}"


@mcp.prompt()
async def cypher_query_help() -> str:
    """Get help and examples for writing Cypher queries.
    
    Returns:
        Comprehensive guide for Cypher query syntax and examples
    """
    return """
# Cypher Query Help

## Basic Syntax

### Reading Data
```cypher
// Find all nodes with a specific label
MATCH (n:Person) RETURN n

// Find nodes with specific properties
MATCH (p:Person {name: "Alice"}) RETURN p

// Find relationships
MATCH (p:Person)-[r:KNOWS]->(friend) RETURN p, r, friend

// Use parameters (recommended for dynamic values)
MATCH (p:Person {name: $name}) RETURN p
```

### Writing Data
```cypher
// Create nodes
CREATE (p:Person {name: "John", age: 30}) RETURN p

// Create relationships
MATCH (a:Person {name: "Alice"}), (b:Person {name: "Bob"})
CREATE (a)-[:KNOWS]->(b)

// Update properties
MATCH (p:Person {name: "John"}) SET p.age = 31

// Delete nodes/relationships
MATCH (p:Person {name: "John"}) DELETE p
```

### Schema Operations
```cypher
// List all labels
CALL db.labels()

// List all relationship types
CALL db.relationshipTypes()

// List all property keys
CALL db.propertyKeys()

// Show constraints
SHOW CONSTRAINTS

// Show indexes
SHOW INDEXES
```

## Best Practices

1. **Use parameters** instead of string concatenation for security
2. **Use LIMIT** to prevent returning too many results
3. **Start with simple queries** and build complexity gradually
4. **Use EXPLAIN** to understand query performance
5. **Use transactions** for multiple related operations

## Common Patterns

### Find connected nodes:
```cypher
MATCH (start:Person {name: $name})-[:KNOWS*1..3]-(connected)
RETURN DISTINCT connected.name
```

### Aggregate data:
```cypher
MATCH (p:Person)-[:KNOWS]->(friend)
RETURN p.name, COUNT(friend) as friend_count
ORDER BY friend_count DESC
```

### Conditional logic:
```cypher
MATCH (p:Person)
RETURN p.name, 
       CASE 
         WHEN p.age < 18 THEN "Minor"
         WHEN p.age < 65 THEN "Adult" 
         ELSE "Senior"
       END as age_group
```
"""


def main() -> None:
    """Main entry point for the Neo4j MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Neo4j MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse"], 
        default="stdio",
        help="Transport mechanism (default: stdio)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=3000,
        help="Port for SSE transport (default: 3000)"
    )
    parser.add_argument(
        "--host", 
        default="localhost",
        help="Host for SSE transport (default: localhost)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Run the server
    try:
        if args.transport == "sse":
            logger.info(f"Starting Neo4j MCP Server on {args.host}:{args.port} (SSE)")
            mcp.run(transport="sse", port=args.port, host=args.host)
        else:
            logger.info("Starting Neo4j MCP Server (stdio)")
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 