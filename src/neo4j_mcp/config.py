"""Configuration management for Neo4j MCP."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jConfig(BaseSettings):
    """Configuration for Neo4j database connection, sourced from env vars / .env."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="localhost", description="Neo4j server hostname")
    port: int = Field(default=7687, description="Neo4j bolt port")
    http_port: int = Field(default=7474, description="Neo4j HTTP/browser port")
    username: str | None = Field(default=None, description="Neo4j username (omit for auth-disabled)")
    password: str | None = Field(default=None, description="Neo4j password (omit for auth-disabled)")
    database: str = Field(default="neo4j", description="Target database name")
    uri_scheme: str = Field(default="bolt", description="URI scheme (bolt, bolt+s, neo4j, neo4j+s)")
    encrypted: bool = Field(default=False, description="Whether to use encrypted connection")

    max_connection_lifetime: int = Field(default=300, description="Max connection lifetime (seconds)")
    max_connection_pool_size: int = Field(default=100, description="Max connection pool size")
    connection_timeout: float = Field(default=30.0, description="Connection timeout (seconds)")

    default_result_limit: int = Field(
        default=100,
        description="Default row cap for read queries when the caller does not specify one",
    )

    @field_validator("port", "http_port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return value

    @field_validator("uri_scheme")
    @classmethod
    def _validate_uri_scheme(cls, value: str) -> str:
        valid_schemes = {"bolt", "bolt+s", "neo4j", "neo4j+s"}
        if value not in valid_schemes:
            raise ValueError(f"URI scheme must be one of {sorted(valid_schemes)}")
        return value

    @property
    def bolt_uri(self) -> str:
        scheme = self.uri_scheme
        if self.encrypted and not scheme.endswith("+s"):
            scheme += "+s"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def http_uri(self) -> str:
        scheme = "https" if self.encrypted else "http"
        return f"{scheme}://{self.host}:{self.http_port}"

    @property
    def auth_tuple(self) -> tuple[str, str] | None:
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def __repr__(self) -> str:
        password_display = "***" if self.password else None
        return (
            "Neo4jConfig("
            f"host={self.host!r}, port={self.port}, "
            f"username={self.username!r}, password={password_display!r}, "
            f"database={self.database!r}, uri_scheme={self.uri_scheme!r})"
        )
