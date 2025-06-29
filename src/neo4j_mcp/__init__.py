"""
Neo4j MCP - Model Context Protocol server and client for Neo4j database access.

This package provides both MCP server and client implementations for connecting
LLMs to Neo4j graph databases with read/write capabilities.
"""

__version__ = "0.1.0"
__author__ = "Neo4j MCP Team"
__email__ = "neo4j-mcp@example.com"

from .config import Neo4jConfig
from .connection import Neo4jConnection

__all__ = [
    "Neo4jConfig", 
    "Neo4jConnection",
    "__version__",
] 