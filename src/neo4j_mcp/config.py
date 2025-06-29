"""Configuration management for Neo4j MCP."""

import os
from typing import Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Neo4jConfig(BaseModel):
    """Configuration for Neo4j database connection."""
    
    host: str = Field(
        default_factory=lambda: os.getenv("NEO4J_HOST", "localhost"),
        description="Neo4j server hostname"
    )
    
    port: int = Field(
        default_factory=lambda: int(os.getenv("NEO4J_PORT", "7687")),
        description="Neo4j server port (bolt protocol, usually 7687)"
    )
    
    http_port: int = Field(
        default_factory=lambda: int(os.getenv("NEO4J_HTTP_PORT", "7474")),
        description="Neo4j HTTP port (browser interface, usually 7474)"
    )
    
    username: Optional[str] = Field(
        default_factory=lambda: os.getenv("NEO4J_USERNAME"),
        description="Neo4j username (optional for auth-disabled databases)"
    )
    
    password: Optional[str] = Field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD"),
        description="Neo4j password (optional for auth-disabled databases)"
    )
    
    database: str = Field(
        default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"),
        description="Neo4j database name"
    )
    
    uri_scheme: str = Field(
        default_factory=lambda: os.getenv("NEO4J_URI_SCHEME", "bolt"),
        description="URI scheme (bolt, bolt+s, neo4j, neo4j+s)"
    )
    
    encrypted: bool = Field(
        default_factory=lambda: os.getenv("NEO4J_ENCRYPTED", "false").lower() == "true",
        description="Whether to use encrypted connection"
    )
    
    max_connection_lifetime: int = Field(
        default=300,
        description="Maximum connection lifetime in seconds"
    )
    
    max_connection_pool_size: int = Field(
        default=100,
        description="Maximum connection pool size"
    )
    
    connection_timeout: float = Field(
        default=30.0,
        description="Connection timeout in seconds"
    )

    class Config:
        """Pydantic configuration."""
        env_prefix = "NEO4J_"
        case_sensitive = False

    @validator("port", "http_port")
    def validate_port(cls, v: int) -> int:
        """Validate port numbers."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @validator("uri_scheme")
    def validate_uri_scheme(cls, v: str) -> str:
        """Validate URI scheme."""
        valid_schemes = {"bolt", "bolt+s", "neo4j", "neo4j+s"}
        if v not in valid_schemes:
            raise ValueError(f"URI scheme must be one of {valid_schemes}")
        return v

    @property
    def bolt_uri(self) -> str:
        """Get the bolt URI for connecting to Neo4j."""
        scheme = self.uri_scheme
        if self.encrypted and not scheme.endswith("+s"):
            scheme += "+s"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def http_uri(self) -> str:
        """Get the HTTP URI for Neo4j browser interface."""
        scheme = "https" if self.encrypted else "http"
        return f"{scheme}://{self.host}:{self.http_port}"

    @property
    def auth_tuple(self) -> Optional[tuple[str, str]]:
        """Get authentication tuple if username and password are provided."""
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def __repr__(self) -> str:
        """String representation hiding sensitive information."""
        password_display = "***" if self.password else None
        return (
            f"Neo4jConfig("
            f"host={self.host!r}, "
            f"port={self.port}, "
            f"username={self.username!r}, "
            f"password={password_display!r}, "
            f"database={self.database!r}, "
            f"uri_scheme={self.uri_scheme!r}"
            f")"
        ) 