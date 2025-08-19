# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Neo4j MCP is a Model Context Protocol (MCP) server implementation that enables LLMs to interact with Neo4j graph databases. It provides both server and client implementations for executing Cypher queries and managing database connections.

## Development Commands

### Installation and Setup
```bash
# Install in editable mode (recommended)
pip install -e .

# Alternative: Setup script for initial configuration
python setup_dev.py

# Install development dependencies
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v --tb=short

# Run a specific test file
pytest tests/test_basic.py

# Run tests with asyncio support (auto-enabled via pytest.ini)
pytest tests/
```

### Code Quality
```bash
# Run ruff linter
ruff check src/

# Run type checking with mypy
mypy src/neo4j_mcp/

# Format/fix code with ruff
ruff check --fix src/
```

### Running the Server
```bash
# Start MCP server (uses .env for configuration)
neo4j-mcp-server

# Start with SSE transport for web clients
neo4j-mcp-server --transport sse --port 3000
```

### Running the Client
```bash
# Test connection
neo4j-mcp-client --query "RETURN 1 as test"

# Execute a query
neo4j-mcp-client --query "MATCH (n) RETURN count(n) as nodeCount"
```

## Architecture

### Core Components

1. **Server Module** (`src/neo4j_mcp/server.py`)
   - FastMCP-based server implementation
   - Manages application lifecycle with Neo4j connection
   - Exposes MCP tools for database operations
   - Handles both stdio and SSE transports

2. **Connection Module** (`src/neo4j_mcp/connection.py`)
   - Wraps synchronous Neo4j driver for async usage
   - Manages connection pooling and lifecycle
   - Provides execute methods for read/write operations
   - Handles authentication and encryption

3. **Configuration** (`src/neo4j_mcp/config.py`)
   - Reads settings from environment variables via `.env` file
   - Supports authenticated and unauthenticated connections
   - Configurable for local, Docker, and cloud deployments (Aura)

4. **Client Module** (`src/neo4j_mcp/client.py`)
   - CLI client for testing and direct database interaction
   - Useful for debugging connection issues

### MCP Tools Available

The server exposes these tools through the MCP protocol:
- `read_cypher_query`: Execute read-only queries
- `write_cypher_query`: Execute write operations
- `get_database_schema`: Retrieve labels and relationship types
- `test_database_connection`: Verify connectivity
- `run_cypher_query`: Execute with explicit read/write mode

### Connection Flow

1. Server reads configuration from `.env` file
2. Creates Neo4jConnection with config parameters
3. Establishes driver connection using `neo4j.GraphDatabase.driver()`
4. Wraps synchronous operations with `asyncio.to_thread()` for async compatibility
5. Manages connection pool and lifecycle through FastMCP lifespan

## Configuration

The project uses environment variables through a `.env` file in the project root. Key variables:
- `NEO4J_HOST`: Database host
- `NEO4J_PORT`: Database port (default: 7687)
- `NEO4J_USERNAME`: Authentication username (leave blank for no auth)
- `NEO4J_PASSWORD`: Authentication password  
- `NEO4J_DATABASE`: Target database (default: neo4j)
- `NEO4J_URI_SCHEME`: Connection scheme (neo4j, neo4j+s for encrypted)
- `NEO4J_ENCRYPTED`: Enable encryption (for cloud services)

## Testing Approach

Tests are located in `tests/` and use pytest with asyncio support. When adding new features:
1. Write unit tests for connection and configuration logic
2. Create integration tests for MCP tool operations
3. Test both authenticated and unauthenticated scenarios
4. Verify error handling for connection failures

## Development Tips

- The server uses a stable synchronous Neo4j driver wrapped for async, avoiding compatibility issues
- Connection pooling is managed by the Neo4j driver with configurable limits
- All database operations should handle `Neo4jError` exceptions appropriately
- Use parameterized queries to prevent injection attacks
- The FastMCP framework handles MCP protocol details and transport