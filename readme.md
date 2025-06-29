# Neo4j MCP - Model Context Protocol for Neo4j

A robust Model Context Protocol (MCP) implementation that enables LLMs to interact with Neo4j graph databases using natural language.

This server uses a stable, synchronous Neo4j driver wrapped for asynchronous use, ensuring reliable connections and compatibility with modern MCP clients.

## 🚀 Features

- **Full Read/Write Access**: Execute both read and write Cypher queries.
- **Flexible Authentication**: Connect to Neo4j with or without authentication.
- **Schema Introspection**: Automatically discover database schema (labels, relationship types).
- **Secure Configuration**: Environment-based configuration using a `.env` file.
- **LLM Integration**: Ready to use with Cursor, Claude Desktop, and other MCP-compatible tools.
- **Robust Error Handling**: Clear error messages for connection and query issues.
- **Parameterized Queries**: Support for safe, parameterized queries to prevent injection.

## 📋 Prerequisites

- Python 3.8+
- A running Neo4j database (local, Docker, or cloud).
- `pip` for installing packages.

## 🔧 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/neo4j-mcp.git
    cd neo4j-mcp
    ```

2.  **Install in editable mode:**
    This is the recommended way to install, as it links the `neo4j-mcp-server` command directly to your source code.
    ```bash
    pip install -e .
    ```

## ⚙️ Configuration

Configuration is managed via a `.env` file in the project root.

1.  **Create a `.env` file.**
2.  **Add your Neo4j connection details.**

### Example 1: Local Neo4j without Authentication
Create a `.env` file with the following content. Leave `NEO4J_USERNAME` and `NEO4J_PASSWORD` blank.
```bash
# .env file
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USERNAME=
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j
```

### Example 2: Local or Cloud Neo4j with Authentication
```bash
# .env file
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-secret-password
NEO4J_DATABASE=neo4j
```

### Example 3: Encrypted Connection (Aura)
For cloud services like Neo4j Aura, use the `neo4j+s` scheme and set `NEO4J_ENCRYPTED` to `true`.
```bash
# .env file
NEO4J_HOST=xxx.databases.neo4j.io
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-aura-password
NEO4J_DATABASE=neo4j
NEO4J_URI_SCHEME=neo4j+s
NEO4J_ENCRYPTED=true
```

## 🏃 Quick Start

With your `.env` file configured and dependencies installed, you can start the server.

```bash
# Start the MCP server
neo4j-mcp-server
```
The server will start and listen for connections over stdio. If you see `INFO:neo4j_mcp.server:Starting Neo4j MCP Server (stdio)`, it's working!

You can also start it with an SSE transport for web-based clients:
```bash
neo4j-mcp-server --transport sse --port 3000
```

## 🔌 LLM Integration (Cursor Example)

1.  Make sure the server is installed and your `.env` file is configured.
2.  In Cursor, open the MCP configuration file (`~/.cursor/mcp.json` or via the `@` symbol > Tools > Settings icon).
3.  Add the following server configuration. The server uses the `.env` file from its own directory, so you don't need to specify credentials here.

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
4.  Restart Cursor. The `@neo4j` tool should now be available and connected.

## 🛠️ Available Tools

-   `read_cypher_query(query, [parameters], [database])`: Execute a read-only query.
-   `write_cypher_query(query, [parameters], [database])`: Execute a write query.
-   `get_database_schema([database])`: Get database labels and relationship types.
-   `test_database_connection()`: Verify the connection and get server info.
-   `run_cypher_query(query, [parameters], [database], [read_only])`: Run a query with explicit read/write mode.

## 🚨 Troubleshooting

-   **`AttributeError: type object 'SessionConfig' has no attribute 'AccessMode'`**: Your `neo4j` library version might be incompatible. The project is tested with `neo4j>=5.15.0`.
-   **`ConnectionError: Neo4j authentication failed`**: Check your `NEO4J_USERNAME` and `NEO4J_PASSWORD` in the `.env` file. If your database has no auth, ensure these are blank.
-   **`ConnectionError: Neo4j service unavailable`**: Make sure your Neo4j database is running and accessible at the specified `NEO4J_HOST` and `NEO4J_PORT`.

---

Made with ❤️ for the Neo4j and MCP communities

