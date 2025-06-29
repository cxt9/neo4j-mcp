"""Neo4j MCP Client implementation for testing and interaction."""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import AnyUrl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jMCPClient:
    """Client for interacting with Neo4j MCP server."""
    
    def __init__(self, server_command: str = "neo4j-mcp-server", server_args: Optional[List[str]] = None):
        """Initialize the MCP client.
        
        Args:
            server_command: Command to start the MCP server
            server_args: Optional arguments for the server command
        """
        self.server_params = StdioServerParameters(
            command=server_command,
            args=server_args or [],
            env=None
        )
        self.session: Optional[ClientSession] = None
    
    async def connect(self) -> None:
        """Connect to the MCP server."""
        try:
            self.read, self.write = await stdio_client(self.server_params).__aenter__()
            self.session = ClientSession(self.read, self.write)
            await self.session.initialize()
            logger.info("Connected to Neo4j MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        logger.info("Disconnected from Neo4j MCP server")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools on the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        tools = await self.session.list_tools()
        return [tool.dict() for tool in tools.tools]
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources on the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        resources = await self.session.list_resources()
        return [resource.dict() for resource in resources.resources]
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts on the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        prompts = await self.session.list_prompts()
        return [prompt.dict() for prompt in prompts.prompts]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        result = await self.session.call_tool(tool_name, arguments)
        return result.content
    
    async def read_resource(self, uri: str) -> str:
        """Read a resource from the server.
        
        Args:
            uri: URI of the resource to read
            
        Returns:
            Resource content as string
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        content, _ = await self.session.read_resource(AnyUrl(uri))
        return content
    
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt from the server.
        
        Args:
            prompt_name: Name of the prompt
            arguments: Optional arguments for the prompt
            
        Returns:
            Prompt content
        """
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        prompt = await self.session.get_prompt(prompt_name, arguments or {})
        # Extract text content from prompt messages
        content = ""
        for message in prompt.messages:
            if hasattr(message.content, 'text'):
                content += message.content.text + "\n"
        return content.strip()
    
    # Convenience methods for Neo4j-specific operations
    
    async def execute_read_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a read-only Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            List of record dictionaries
        """
        args = {"query": query}
        if parameters:
            args["parameters"] = parameters
        
        result = await self.call_tool("read_cypher_query", args)
        return result
    
    async def execute_write_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a write Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            Query execution statistics
        """
        args = {"query": query}
        if parameters:
            args["parameters"] = parameters
        
        result = await self.call_tool("write_cypher_query", args)
        return result
    
    async def get_schema(self) -> Dict[str, Any]:
        """Get the database schema."""
        result = await self.call_tool("get_database_schema", {})
        return result
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the database connection."""
        result = await self.call_tool("test_database_connection", {})
        return result
    
    async def get_schema_resource(self) -> str:
        """Get the schema as a formatted resource."""
        return await self.read_resource("neo4j://schema")
    
    async def get_connection_info(self) -> str:
        """Get connection information as a formatted resource."""
        return await self.read_resource("neo4j://connection")
    
    async def get_cypher_help(self) -> str:
        """Get Cypher query help."""
        return await self.get_prompt("cypher_query_help")


async def interactive_client(client: Neo4jMCPClient) -> None:
    """Run an interactive client session."""
    print("🗂️  Neo4j MCP Interactive Client")
    print("Type 'help' for available commands, 'quit' to exit")
    print()
    
    while True:
        try:
            command = input("neo4j-mcp> ").strip()
            
            if not command:
                continue
            
            if command in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break
            
            elif command == "help":
                print("""
Available commands:
  help                          - Show this help message
  tools                        - List available tools
  resources                    - List available resources  
  prompts                      - List available prompts
  schema                       - Show database schema
  connection                   - Show connection info
  test                         - Test database connection
  cypher-help                  - Get Cypher query help
  read <query>                 - Execute read query
  write <query>                - Execute write query
  read-file <file>             - Execute read query from file
  write-file <file>            - Execute write query from file
  quit                         - Exit the client

Examples:
  read MATCH (n) RETURN count(n)
  write CREATE (p:Person {name: 'Alice'}) RETURN p
  read-file queries/get_people.cypher
""")
            
            elif command == "tools":
                tools = await client.list_tools()
                print(f"📋 Available tools ({len(tools)}):")
                for tool in tools:
                    print(f"  - {tool['name']}: {tool['description']}")
            
            elif command == "resources":
                resources = await client.list_resources()
                print(f"📄 Available resources ({len(resources)}):")
                for resource in resources:
                    print(f"  - {resource['uri']}: {resource['description']}")
            
            elif command == "prompts":
                prompts = await client.list_prompts()
                print(f"💬 Available prompts ({len(prompts)}):")
                for prompt in prompts:
                    print(f"  - {prompt['name']}: {prompt['description']}")
            
            elif command == "schema":
                schema_text = await client.get_schema_resource()
                print(schema_text)
            
            elif command == "connection":
                connection_info = await client.get_connection_info()
                print(connection_info)
            
            elif command == "test":
                result = await client.test_connection()
                if result.get("connected"):
                    print("✅ Database connection successful")
                    if "components" in result:
                        print("Server components:")
                        for component in result["components"]:
                            versions = ", ".join(component["versions"])
                            print(f"  - {component['name']}: {versions} ({component['edition']})")
                else:
                    print(f"❌ Database connection failed: {result.get('error', 'Unknown error')}")
            
            elif command == "cypher-help":
                help_text = await client.get_cypher_help()
                print(help_text)
            
            elif command.startswith("read "):
                query = command[5:].strip()
                if query:
                    try:
                        result = await client.execute_read_query(query)
                        print(f"📊 Query returned {len(result)} records:")
                        for i, record in enumerate(result[:10]):  # Show first 10 records
                            print(f"  {i+1}: {json.dumps(record, indent=2, default=str)}")
                        if len(result) > 10:
                            print(f"  ... and {len(result) - 10} more records")
                    except Exception as e:
                        print(f"❌ Query failed: {e}")
                else:
                    print("❌ Please provide a query")
            
            elif command.startswith("write "):
                query = command[6:].strip()
                if query:
                    try:
                        result = await client.execute_write_query(query)
                        print("✅ Write query executed successfully:")
                        print(json.dumps(result, indent=2, default=str))
                    except Exception as e:
                        print(f"❌ Query failed: {e}")
                else:
                    print("❌ Please provide a query")
            
            elif command.startswith("read-file "):
                filename = command[10:].strip()
                try:
                    with open(filename, 'r') as f:
                        query = f.read().strip()
                    if query:
                        result = await client.execute_read_query(query)
                        print(f"📊 Query from {filename} returned {len(result)} records:")
                        for i, record in enumerate(result[:10]):
                            print(f"  {i+1}: {json.dumps(record, indent=2, default=str)}")
                        if len(result) > 10:
                            print(f"  ... and {len(result) - 10} more records")
                    else:
                        print("❌ File is empty")
                except FileNotFoundError:
                    print(f"❌ File not found: {filename}")
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            elif command.startswith("write-file "):
                filename = command[11:].strip()
                try:
                    with open(filename, 'r') as f:
                        query = f.read().strip()
                    if query:
                        result = await client.execute_write_query(query)
                        print(f"✅ Write query from {filename} executed successfully:")
                        print(json.dumps(result, indent=2, default=str))
                    else:
                        print("❌ File is empty")
                except FileNotFoundError:
                    print(f"❌ File not found: {filename}")
                except Exception as e:
                    print(f"❌ Error: {e}")
            
            else:
                print(f"❌ Unknown command: {command}")
                print("Type 'help' for available commands")
            
            print()  # Add blank line for readability
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print()


async def run_client() -> None:
    """Run the Neo4j MCP client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Neo4j MCP Client")
    parser.add_argument(
        "--server-command",
        default="neo4j-mcp-server",
        help="Command to start the MCP server (default: neo4j-mcp-server)"
    )
    parser.add_argument(
        "--server-args",
        nargs="*",
        help="Arguments to pass to the server command"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        default=True,
        help="Run in interactive mode (default: True)"
    )
    parser.add_argument(
        "--query",
        help="Execute a single query and exit"
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        default=True,
        help="Execute query as read-only (default: True)"
    )
    
    args = parser.parse_args()
    
    client = Neo4jMCPClient(
        server_command=args.server_command,
        server_args=args.server_args
    )
    
    try:
        await client.connect()
        
        if args.query:
            # Execute single query and exit
            if args.read_only:
                result = await client.execute_read_query(args.query)
                print(json.dumps(result, indent=2, default=str))
            else:
                result = await client.execute_write_query(args.query)
                print(json.dumps(result, indent=2, default=str))
        else:
            # Run interactive mode
            await interactive_client(client)
            
    except Exception as e:
        logger.error(f"Client error: {e}")
        sys.exit(1)
    finally:
        await client.disconnect()


def main() -> None:
    """Main entry point for the Neo4j MCP client."""
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\n👋 Client stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 