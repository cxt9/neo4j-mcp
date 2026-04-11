"""Tests for Neo4j MCP configuration and connection."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import neo4j
import pytest

from neo4j_mcp.config import Neo4jConfig
from neo4j_mcp.connection import Neo4jConnection


class TestNeo4jConfig:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in list(os.environ):
            if key.startswith("NEO4J_"):
                monkeypatch.delenv(key, raising=False)
        config = Neo4jConfig(_env_file=None)
        assert config.host == "localhost"
        assert config.port == 7687
        assert config.database == "neo4j"
        assert config.uri_scheme == "bolt"
        assert config.encrypted is False

    def test_bolt_uri(self) -> None:
        config = Neo4jConfig(host="example.com", port=7687, uri_scheme="bolt")
        assert config.bolt_uri == "bolt://example.com:7687"

    def test_encrypted_upgrades_scheme(self) -> None:
        config = Neo4jConfig(host="example.com", port=7687, uri_scheme="bolt", encrypted=True)
        assert config.bolt_uri == "bolt+s://example.com:7687"

    def test_http_uri(self) -> None:
        config = Neo4jConfig(host="example.com", http_port=7474, encrypted=False)
        assert config.http_uri == "http://example.com:7474"

    def test_auth_tuple(self) -> None:
        assert Neo4jConfig(username="u", password="p").auth_tuple == ("u", "p")
        assert Neo4jConfig(username=None, password=None).auth_tuple is None
        assert Neo4jConfig(username="u", password=None).auth_tuple is None

    def test_env_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NEO4J_HOST", "env-host")
        monkeypatch.setenv("NEO4J_PORT", "9999")
        monkeypatch.setenv("NEO4J_USERNAME", "env-user")
        monkeypatch.setenv("NEO4J_PASSWORD", "env-pass")
        config = Neo4jConfig(_env_file=None)
        assert config.host == "env-host"
        assert config.port == 9999
        assert config.username == "env-user"
        assert config.password == "env-pass"

    def test_port_validation(self) -> None:
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            Neo4jConfig(port=0)
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            Neo4jConfig(port=70000)

    def test_uri_scheme_validation(self) -> None:
        with pytest.raises(ValueError, match="URI scheme must be one of"):
            Neo4jConfig(uri_scheme="invalid")

    def test_repr_masks_password(self) -> None:
        config = Neo4jConfig(username="u", password="supersecret")
        rendered = repr(config)
        assert "supersecret" not in rendered
        assert "***" in rendered


class TestNeo4jConnection:
    @pytest.fixture
    def config(self) -> Neo4jConfig:
        return Neo4jConfig(
            host="localhost", port=7687, username="neo4j", password="password", database="neo4j"
        )

    @pytest.fixture
    def connection(self, config: Neo4jConfig) -> Neo4jConnection:
        return Neo4jConnection(config)

    def test_init(self, connection: Neo4jConnection, config: Neo4jConfig) -> None:
        assert connection.config == config
        assert connection._driver is None
        assert not connection.is_connected

    async def test_connect_success(self, connection: Neo4jConnection) -> None:
        with patch("neo4j_mcp.connection.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_gdb.driver.return_value = mock_driver

            await connection.connect()

            assert connection.is_connected
            mock_gdb.driver.assert_called_once()
            mock_driver.verify_connectivity.assert_called_once()

    async def test_connect_auth_error(self, connection: Neo4jConnection) -> None:
        from neo4j.exceptions import AuthError

        with patch("neo4j_mcp.connection.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_driver.verify_connectivity.side_effect = AuthError("Auth failed")
            mock_gdb.driver.return_value = mock_driver

            with pytest.raises(ConnectionError, match="Neo4j authentication failed"):
                await connection.connect()

    async def test_connect_is_idempotent(self, connection: Neo4jConnection) -> None:
        with patch("neo4j_mcp.connection.GraphDatabase") as mock_gdb:
            mock_gdb.driver.return_value = MagicMock()
            await connection.connect()
            await connection.connect()
            mock_gdb.driver.assert_called_once()

    async def test_close(self, connection: Neo4jConnection) -> None:
        mock_driver = MagicMock()
        connection._driver = mock_driver
        await connection.close()
        mock_driver.close.assert_called_once()
        assert not connection.is_connected

    async def test_empty_query_rejected(self, connection: Neo4jConnection) -> None:
        connection._driver = MagicMock()
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await connection.execute_read_query("")
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await connection.execute_read_query("   ")

    async def test_read_query_shape(self, connection: Neo4jConnection) -> None:
        mock_record = MagicMock()
        mock_record.data.return_value = {"name": "Alice", "age": 30}

        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([mock_record])
        mock_result.consume.return_value = _summary_stub()

        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = False
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        connection._driver = mock_driver

        result = await connection.execute_read_query("MATCH (n) RETURN n")

        assert result["record_count"] == 1
        assert result["records"] == [{"name": "Alice", "age": 30}]
        assert result["truncated"] is False
        assert "stats" in result
        mock_session.run.assert_called_once_with("MATCH (n) RETURN n", {})

    async def test_read_query_truncates(self, connection: Neo4jConnection) -> None:
        records = []
        for i in range(5):
            r = MagicMock()
            r.data.return_value = {"i": i}
            records.append(r)

        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter(records)
        mock_result.consume.return_value = _summary_stub()

        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = False
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        connection._driver = mock_driver

        result = await connection.execute_read_query("MATCH (n) RETURN n", limit=3)
        assert result["record_count"] == 3
        assert result["truncated"] is True


class TestSerialization:
    @pytest.fixture
    def connection(self) -> Neo4jConnection:
        return Neo4jConnection(Neo4jConfig())

    def test_scalars(self, connection: Neo4jConnection) -> None:
        ser = Neo4jConnection._serialize_value
        assert ser("s") == "s"
        assert ser(42) == 42
        assert ser(True) is True
        assert ser(None) is None
        assert ser([1, 2]) == [1, 2]
        assert ser({"k": "v"}) == {"k": "v"}

    def test_bytes_to_hex(self) -> None:
        assert Neo4jConnection._serialize_value(b"\x00\xff") == "00ff"

    def test_temporal_types(self) -> None:
        dt = neo4j.time.DateTime(2024, 1, 2, 3, 4, 5)
        serialized = Neo4jConnection._serialize_value(dt)
        assert isinstance(serialized, str)
        assert "2024" in serialized

    def test_node_preserves_identity(self) -> None:
        node = MagicMock(spec=neo4j.graph.Node)
        node.element_id = "4:abc:1"
        node.labels = frozenset({"Person"})
        node.__iter__ = lambda self: iter([("name", "Alice")])
        node.keys = lambda: ["name"]
        node.__getitem__ = lambda self, k: {"name": "Alice"}[k]

        serialized = Neo4jConnection._serialize_value(node)
        assert serialized["_type"] == "node"
        assert serialized["_id"] == "4:abc:1"
        assert serialized["_labels"] == ["Person"]
        assert serialized["_properties"] == {"name": "Alice"}


def _summary_stub() -> neo4j.ResultSummary:
    counters = MagicMock()
    counters.nodes_created = 0
    counters.nodes_deleted = 0
    counters.relationships_created = 0
    counters.relationships_deleted = 0
    counters.properties_set = 0
    counters.labels_added = 0
    counters.labels_removed = 0
    counters.indexes_added = 0
    counters.indexes_removed = 0
    counters.constraints_added = 0
    counters.constraints_removed = 0
    summary = MagicMock()
    summary.counters = counters
    return summary


if __name__ == "__main__":
    pytest.main([__file__])
