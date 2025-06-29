# Neo4j MCP - Model Context Protocol for Neo4j

A comprehensive Model Context Protocol (MCP) implementation that enables LLMs (Large Language Models) like Claude, ChatGPT, and others to interact with Neo4j graph databases using natural language.

## 🚀 Features

- **Full Read/Write Access**: Execute both read and write Cypher queries
- **Schema Introspection**: Automatic discovery of database schema, labels, relationships, and constraints
- **Secure Configuration**: Environment-based configuration with sensible defaults
- **Multi-Transport Support**: Works with stdio and SSE transports
- **Interactive Client**: Built-in client for testing and development
- **LLM Integration**: Ready-to-use with Claude Desktop, Cursor, VS Code, and other MCP-compatible tools
- **Async Architecture**: High-performance async implementation
- **Error Handling**: Comprehensive error handling and logging
- **Parameter Support**: Safe parameterized queries to prevent injection attacks

## 📋 Prerequisites

- Python 3.8+
- Neo4j database (local or cloud)
- uv package manager (recommended) or pip

## 🔧 Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/your-repo/neo4j-mcp.git
cd neo4j-mcp

# Install with uv
uv sync
```

### Using pip

```bash
# Clone the repository  
git clone https://github.com/your-repo/neo4j-mcp.git
cd neo4j-mcp

# Install dependencies
pip install -e .
```

### From PyPI (when published)

```bash
pip install neo4j-mcp
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in your project root or set these environment variables:

```bash
# Required settings
NEO4J_HOST=localhost                # Neo4j server hostname
NEO4J_PORT=7687                     # Bolt protocol port
NEO4J_HTTP_PORT=7474               # HTTP browser port

# Authentication (optional for auth-disabled databases)
NEO4J_USERNAME=neo4j               # Database username
NEO4J_PASSWORD=your-password       # Database password

# Database settings
NEO4J_DATABASE=neo4j               # Database name
NEO4J_URI_SCHEME=bolt              # Connection scheme (bolt, bolt+s, neo4j, neo4j+s)
NEO4J_ENCRYPTED=false              # Use encrypted connection
```

### Example Configurations

#### Local Neo4j (no authentication)
```bash
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USERNAME=
NEO4J_PASSWORD=
```

#### Local Neo4j (with authentication)
```bash
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

#### Neo4j Aura (cloud)
```bash
NEO4J_HOST=xxx.databases.neo4j.io
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-aura-password
NEO4J_URI_SCHEME=neo4j+s
NEO4J_ENCRYPTED=true
```

## 🏃 Quick Start

### 1. Start the MCP Server

```bash
# Using the installed command
neo4j-mcp-server

# Or with custom options
neo4j-mcp-server --transport sse --port 3000

# Or using Python module
python -m neo4j_mcp.server
```

### 2. Test with the Interactive Client

```bash
# Start the interactive client
neo4j-mcp-client

# Or test a single query
neo4j-mcp-client --query "MATCH (n) RETURN count(n) as total_nodes"
```

### 3. Basic Usage Examples

Once connected, try these commands in the interactive client:

```bash
# Test the connection
neo4j-mcp> test

# View database schema
neo4j-mcp> schema

# Execute a read query
neo4j-mcp> read MATCH (n) RETURN count(n) as total_nodes

# Execute a write query  
neo4j-mcp> write CREATE (p:Person {name: 'Alice', age: 30}) RETURN p

# Get help with Cypher syntax
neo4j-mcp> cypher-help
```

## 🔌 LLM Integration

### Claude Desktop

Add this configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "neo4j-mcp": {
      "command": "neo4j-mcp-server",
      "args": ["--transport", "stdio"],
      "env": {
        "NEO4J_HOST": "localhost",
        "NEO4J_PORT": "7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "your-password",
        "NEO4J_DATABASE": "neo4j"
      }
    }
  }
}
```

### Cursor / VS Code

Configure your MCP settings to include:

```json
{
  "mcp.servers": {
    "neo4j": {
      "command": "neo4j-mcp-server",
      "transport": "stdio"
    }
  }
}
```

## 🛠️ Available Tools

The MCP server provides these tools for LLMs:

### Query Tools

- **`read_cypher_query`** - Execute read-only Cypher queries safely
- **`write_cypher_query`** - Execute write Cypher queries (CREATE, UPDATE, DELETE)
- **`run_cypher_query`** - Execute queries with read/write mode selection

### Schema Tools

- **`get_database_schema`** - Get complete database schema information
- **`test_database_connection`** - Test connection and get server info

### Resources

- **`neo4j://schema`** - Formatted schema information
- **`neo4j://connection`** - Connection status and server details

### Prompts

- **`cypher_query_help`** - Comprehensive Cypher query syntax and examples

## 📊 Example Queries

### Schema Exploration
```cypher
-- List all node labels
CALL db.labels()

-- List all relationship types
CALL db.relationshipTypes()

-- Show constraints
SHOW CONSTRAINTS
```

### Data Queries
```cypher
-- Count all nodes
MATCH (n) RETURN count(n) as total_nodes

-- Find nodes by label
MATCH (p:Person) RETURN p LIMIT 10

-- Complex relationship query
MATCH (p:Person)-[:KNOWS]->(friend:Person)
WHERE p.age > 25
RETURN p.name, collect(friend.name) as friends
```

### Data Modification
```cypher
-- Create nodes
CREATE (p:Person {name: 'Alice', age: 30, city: 'New York'})

-- Create relationships
MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'})
CREATE (a)-[:KNOWS {since: 2020}]->(b)

-- Update properties
MATCH (p:Person {name: 'Alice'})
SET p.age = 31, p.updated = timestamp()
```

## 🔒 Security

- **Parameterized Queries**: Always use parameters for dynamic values
- **Environment Variables**: Store credentials securely in environment variables
- **Connection Encryption**: Support for encrypted connections (TLS/SSL)
- **Error Sanitization**: Sensitive information is not exposed in error messages

### Safe Query Examples

```python
# ✅ Good - using parameters
query = "MATCH (p:Person {name: $name}) RETURN p"
parameters = {"name": "Alice"}

# ❌ Bad - string concatenation
query = f"MATCH (p:Person {{name: '{name}'}}) RETURN p"
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=neo4j_mcp

# Run specific test file
uv run pytest tests/test_connection.py
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Development Server

```bash
# Run in development mode with auto-reload
mcp dev src/neo4j_mcp/server.py

# With additional dependencies
mcp dev src/neo4j_mcp/server.py --with pandas --with matplotlib
```

## 📚 Advanced Usage

### Custom Configuration

```python
from neo4j_mcp import Neo4jConfig, Neo4jConnection

# Custom configuration
config = Neo4jConfig(
    host="localhost",
    port=7687,
    username="neo4j", 
    password="password",
    database="custom_db",
    encrypted=True
)

# Use with connection
async with Neo4jConnection(config) as conn:
    result = await conn.execute_read_query("MATCH (n) RETURN count(n)")
    print(result)
```

### Programmatic Usage

```python
from neo4j_mcp.client import Neo4jMCPClient

async def example():
    client = Neo4jMCPClient()
    await client.connect()
    
    # Execute queries
    result = await client.execute_read_query("MATCH (n) RETURN count(n)")
    print(f"Total nodes: {result[0]['count(n)']}")
    
    # Get schema
    schema = await client.get_schema()
    print(f"Labels: {schema['labels']}")
    
    await client.disconnect()
```

## 🚨 Troubleshooting

### Connection Issues

1. **Verify Neo4j is running**: Check if Neo4j service is active
2. **Check credentials**: Ensure username/password are correct
3. **Network connectivity**: Test connection with `neo4j-mcp-client --query "RETURN 1"`
4. **Port accessibility**: Verify ports 7687 (Bolt) and 7474 (HTTP) are accessible

### Common Error Messages

- **"Authentication failed"**: Check NEO4J_USERNAME and NEO4J_PASSWORD
- **"Service unavailable"**: Neo4j server is not running or unreachable
- **"Database not found"**: Check NEO4J_DATABASE setting

### Debug Mode

```bash
# Enable debug logging
NEO4J_LOG_LEVEL=DEBUG neo4j-mcp-server

# Or in the client
neo4j-mcp-client --log-level DEBUG
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run tests and linting: `uv run pytest && uv run ruff check .`
5. Commit your changes: `git commit -am 'Add some feature'`
6. Push to the branch: `git push origin feature/your-feature`
7. Submit a pull request

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Neo4j](https://neo4j.com/) graph database
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk) Python SDK

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/neo4j-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/neo4j-mcp/discussions)
- **Documentation**: [Full Documentation](https://your-repo.github.io/neo4j-mcp/)

---

Made with ❤️ for the Neo4j and MCP communities

