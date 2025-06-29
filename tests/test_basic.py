"""Basic tests for Neo4j MCP functionality."""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from neo4j_mcp.config import Neo4jConfig
from neo4j_mcp.connection import Neo4jConnection


class TestNeo4jConfig:
    """Test Neo4j configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = Neo4jConfig()
        assert config.host == "localhost"
        assert config.port == 7687
        assert config.http_port == 7474
        assert config.database == "neo4j"
        assert config.uri_scheme == "bolt"
        assert config.encrypted is False
    
    def test_bolt_uri(self):
        """Test bolt URI generation."""
        config = Neo4jConfig(
            host="example.com",
            port=7687,
            uri_scheme="bolt"
        )
        assert config.bolt_uri == "bolt://example.com:7687"
    
    def test_encrypted_uri(self):
        """Test encrypted URI generation."""
        config = Neo4jConfig(
            host="example.com",
            port=7687,
            uri_scheme="bolt",
            encrypted=True
        )
        assert config.bolt_uri == "bolt+s://example.com:7687"
    
    def test_http_uri(self):
        """Test HTTP URI generation."""
        config = Neo4jConfig(
            host="example.com",
            http_port=7474,
            encrypted=False
        )
        assert config.http_uri == "http://example.com:7474"
    
    def test_auth_tuple(self):
        """Test authentication tuple."""
        config = Neo4jConfig(username="user", password="pass")
        assert config.auth_tuple == ("user", "pass")
        
        config_no_auth = Neo4jConfig()
        assert config_no_auth.auth_tuple is None
    
    def test_env_variables(self):
        """Test environment variable loading."""
        with patch.dict(os.environ, {
            'NEO4J_HOST': 'env-host',
            'NEO4J_PORT': '9999',
            'NEO4J_USERNAME': 'env-user',
            'NEO4J_PASSWORD': 'env-pass'
        }):
            config = Neo4jConfig()
            assert config.host == 'env-host'
            assert config.port == 9999
            assert config.username == 'env-user'
            assert config.password == 'env-pass'
    
    def test_port_validation(self):
        """Test port validation."""
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            Neo4jConfig(port=0)
        
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            Neo4jConfig(port=70000)
    
    def test_uri_scheme_validation(self):
        """Test URI scheme validation."""
        with pytest.raises(ValueError, match="URI scheme must be one of"):
            Neo4jConfig(uri_scheme="invalid")


class TestNeo4jConnection:
    """Test Neo4j connection functionality."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Neo4jConfig(
            host="localhost",
            port=7687,
            username="neo4j",
            password="password",
            database="neo4j"
        )
    
    @pytest.fixture
    def connection(self, config):
        """Create a test connection."""
        return Neo4jConnection(config)
    
    def test_connection_init(self, connection, config):
        """Test connection initialization."""
        assert connection.config == config
        assert connection._driver is None
        assert not connection.is_connected
    
    @patch('neo4j_mcp.connection.GraphDatabase')
    async def test_connect_success(self, mock_graph_db, connection):
        """Test successful connection."""
        mock_driver = AsyncMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.verify_connectivity = AsyncMock()
        
        await connection.connect()
        
        assert connection.is_connected
        mock_graph_db.driver.assert_called_once()
        mock_driver.verify_connectivity.assert_called_once()
    
    @patch('neo4j_mcp.connection.GraphDatabase')
    async def test_connect_auth_error(self, mock_graph_db, connection):
        """Test connection with authentication error."""
        from neo4j.exceptions import AuthError
        
        mock_driver = AsyncMock()
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.verify_connectivity.side_effect = AuthError("Auth failed")
        
        with pytest.raises(ConnectionError, match="Neo4j authentication failed"):
            await connection.connect()
    
    async def test_close(self, connection):
        """Test connection closure."""
        # Mock a connected driver
        mock_driver = AsyncMock()
        connection._driver = mock_driver
        
        await connection.close()
        
        mock_driver.close.assert_called_once()
        assert connection._driver is None
        assert not connection.is_connected
    
    @patch('neo4j_mcp.connection.GraphDatabase')
    async def test_execute_read_query(self, mock_graph_db, connection):
        """Test read query execution."""
        # Setup mocks
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = MagicMock()
        
        mock_graph_db.driver.return_value = mock_driver
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_session.run.return_value = mock_result
        
        # Mock record iteration
        mock_record.keys.return_value = ["name", "age"]
        mock_record.__getitem__.side_effect = lambda key: {"name": "Alice", "age": 30}[key]
        mock_result.__aiter__.return_value = [mock_record]
        
        # Connect and execute query
        await connection.connect()
        result = await connection.execute_read_query("MATCH (n) RETURN n")
        
        assert len(result) == 1
        mock_session.run.assert_called_once_with("MATCH (n) RETURN n", {})
    
    async def test_serialize_neo4j_value(self, connection):
        """Test Neo4j value serialization."""
        # Test basic types
        assert connection._serialize_neo4j_value("string") == "string"
        assert connection._serialize_neo4j_value(42) == 42
        assert connection._serialize_neo4j_value(True) is True
        assert connection._serialize_neo4j_value(None) is None
        
        # Test list
        assert connection._serialize_neo4j_value([1, 2, 3]) == [1, 2, 3]
        
        # Test dict
        assert connection._serialize_neo4j_value({"key": "value"}) == {"key": "value"}
    
    async def test_session_not_connected(self, connection):
        """Test session creation when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to Neo4j"):
            async with connection.session():
                pass
    
    async def test_empty_query_validation(self, connection):
        """Test validation of empty queries."""
        # Mock connection
        mock_driver = AsyncMock()
        connection._driver = mock_driver
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await connection.execute_read_query("")
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await connection.execute_read_query("   ")


class TestServerIntegration:
    """Integration tests for the MCP server."""
    
    @patch('neo4j_mcp.server.Neo4jConnection')
    async def test_server_tools_available(self, mock_connection_class):
        """Test that server tools are properly registered."""
        from neo4j_mcp.server import mcp
        
        # Get registered tools
        tools = []
        for name, func in mcp._tools.items():
            tools.append(name)
        
        expected_tools = [
            'read_cypher_query',
            'write_cypher_query',
            'get_database_schema',
            'test_database_connection',
            'run_cypher_query'
        ]
        
        for tool in expected_tools:
            assert tool in tools
    
    @patch('neo4j_mcp.server.Neo4jConnection')
    async def test_server_resources_available(self, mock_connection_class):
        """Test that server resources are properly registered."""
        from neo4j_mcp.server import mcp
        
        # Get registered resources
        resources = []
        for pattern, func in mcp._resources.items():
            resources.append(pattern)
        
        expected_resources = [
            'neo4j://schema',
            'neo4j://connection'
        ]
        
        for resource in expected_resources:
            assert resource in resources


if __name__ == "__main__":
    pytest.main([__file__]) 