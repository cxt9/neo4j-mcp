# Neo4j MCP

A Model Context Protocol server that lets Claude (and other MCP clients) query and mutate Neo4j graph databases. Ships as both a standalone MCP server and a **Claude Code plugin** you can install once and reuse from any project.

Each project supplies its own Neo4j credentials via a local `.env` file, so the same plugin can target different databases depending on which folder Claude Code is opened in.

---

## Features

- One consolidated `cypher_query` tool with explicit `read` / `write` mode.
- Schema introspection: labels, relationship types, and property keys.
- Full result serialization — preserves node/relationship `element_id`, labels, types, and Neo4j temporal/spatial values.
- Result-size guard with truncation flag, so a runaway `MATCH (n)` won't blow up the response.
- Per-project credentials through `.env` (loaded by `python-dotenv` from the working directory).
- Works with stdio (Claude Code, Claude Desktop, Cursor) and SSE.

## Prerequisites

- Python 3.10+
- A reachable Neo4j database (local, Docker, or Aura)
- `pip` (or `uv`, `pipx`)

## Install the Python package

The plugin shells out to a console script called `neo4j-mcp-server`, so the package needs to be on your PATH first.

```bash
git clone https://github.com/your-repo/neo4j-mcp.git
cd neo4j-mcp
pip install -e .
```

Verify it landed:

```bash
which neo4j-mcp-server
neo4j-mcp-server --help
```

> Tip: if you use `pipx`, `pipx install -e .` keeps the server isolated from your global Python.

## Use it as a Claude Code plugin

The repo ships a plugin manifest at `.claude-plugin/plugin.json`. Once installed at the user level, the `neo4j` MCP server is available in **every** Claude Code session, on any project.

### 1. Install the plugin

From inside Claude Code:

```
/plugin install /absolute/path/to/neo4j-mcp
```

That registers the manifest globally. (You can also add it via a marketplace if you publish one — see Claude Code's plugin docs.)

### 2. Drop a `.env` in any project that should talk to Neo4j

The MCP server inherits Claude Code's working directory, so `python-dotenv` picks up whatever `.env` lives in that project's root. Different folders → different databases, no plugin reconfiguration needed.

```bash
# my-project/.env
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-secret
NEO4J_DATABASE=neo4j
```

For Aura / encrypted connections:

```bash
NEO4J_HOST=xxx.databases.neo4j.io
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-aura-password
NEO4J_URI_SCHEME=neo4j+s
NEO4J_ENCRYPTED=true
```

For an unauthenticated local instance, leave `NEO4J_USERNAME` and `NEO4J_PASSWORD` blank.

> **Don't commit `.env`.** Add it to `.gitignore` in every project.

### 3. Use it from Claude Code

Open the project, then ask Claude things like:

- "What labels and relationship types exist in this graph?"
- "Find the 10 most-connected `Person` nodes."
- "Create a `Movie` node titled *Inception* released in 2010."

Claude will call the `cypher_query`, `get_database_schema`, and `test_database_connection` tools as needed.

## Use it without Claude Code

The same package works as a plain MCP server for any MCP-compatible client.

### Claude Desktop / Cursor

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or your Cursor MCP config:

```json
{
  "mcpServers": {
    "neo4j": {
      "command": "neo4j-mcp-server",
      "args": []
    }
  }
}
```

Set the credentials by either putting a `.env` next to wherever the client launches the process, or by exporting `NEO4J_*` variables in the environment block.

### SSE transport (web clients)

```bash
neo4j-mcp-server --transport sse --host 0.0.0.0 --port 3000
```

### Standalone CLI

A small client is bundled for one-off testing:

```bash
neo4j-mcp-client --test
neo4j-mcp-client --schema
neo4j-mcp-client --query "MATCH (n) RETURN count(n) AS nodes"
neo4j-mcp-client --write --query "CREATE (p:Person {name: 'Alice'}) RETURN p"
```

## Configuration reference

All settings are read from environment variables (or a `.env` file in the working directory).

| Variable | Default | Description |
|---|---|---|
| `NEO4J_HOST` | `localhost` | Bolt host |
| `NEO4J_PORT` | `7687` | Bolt port |
| `NEO4J_HTTP_PORT` | `7474` | Browser/HTTP port (informational) |
| `NEO4J_USERNAME` | _(empty)_ | Leave blank for unauthenticated databases |
| `NEO4J_PASSWORD` | _(empty)_ | |
| `NEO4J_DATABASE` | `neo4j` | Default database |
| `NEO4J_URI_SCHEME` | `bolt` | One of `bolt`, `bolt+s`, `neo4j`, `neo4j+s` |
| `NEO4J_ENCRYPTED` | `false` | Set `true` for Aura / TLS |
| `NEO4J_DEFAULT_RESULT_LIMIT` | `100` | Row cap for read queries when none is supplied |
| `NEO4J_MAX_CONNECTION_POOL_SIZE` | `100` | Driver pool size |
| `NEO4J_CONNECTION_TIMEOUT` | `30.0` | Seconds |

## Tools exposed by the MCP server

| Tool | Purpose |
|---|---|
| `cypher_query(query, mode="read"\|"write", parameters?, database?, limit?)` | Run any Cypher query. Use `mode="write"` for `CREATE`/`MERGE`/`SET`/`DELETE`, even if you also `RETURN` rows. Returns `{records, record_count, truncated, stats}`. |
| `get_database_schema(database?)` | Returns labels, relationship types, and property keys. |
| `test_database_connection()` | Verifies connectivity, returns the server agent string and Bolt protocol version. |

Resources: `neo4j://schema`, `neo4j://connection`. Prompt: `cypher_query_help`.

## Development

```bash
pip install -e ".[dev]"
pytest                    # 21 unit tests, no live database needed
ruff check src/ tests/
mypy src/neo4j_mcp/
```

## Troubleshooting

- **`Neo4j authentication failed`** — username/password mismatch. For unauthenticated DBs, leave both blank (don't set them to `neo4j`/`neo4j`).
- **`Neo4j service unavailable`** — DB is down or `NEO4J_HOST` / `NEO4J_PORT` are wrong. Try `cypher-shell -a bolt://$NEO4J_HOST:$NEO4J_PORT` to confirm.
- **Plugin can't find `neo4j-mcp-server`** — the console script isn't on the PATH that Claude Code inherits. Install with `pipx` or make sure your shell rc file exports the right `PATH` for GUI apps. On macOS, GUI apps don't read `~/.zshrc`; use `launchctl setenv PATH ...` or install into `/usr/local/bin`.
- **`truncated: true` on a read** — bump `limit` on the call, or set `NEO4J_DEFAULT_RESULT_LIMIT` higher in `.env`.

---

MIT licensed.
