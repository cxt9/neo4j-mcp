#!/usr/bin/env python3
"""Simple task runner for Neo4j MCP development."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, capture_output: bool = False) -> int:
    """Run a command and return exit code."""
    print(f"Running: {cmd}")
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return result.returncode
        else:
            return subprocess.run(cmd, shell=True).returncode
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130


def setup_dev():
    """Set up development environment."""
    return run_command("python setup_dev.py")


def test():
    """Run tests."""
    return run_command("uv run pytest tests/ -v")


def test_coverage():
    """Run tests with coverage."""
    return run_command("uv run pytest tests/ -v --cov=neo4j_mcp --cov-report=html --cov-report=term")


def lint():
    """Run linting."""
    exit_code = 0
    exit_code |= run_command("uv run ruff check .")
    exit_code |= run_command("uv run mypy src/neo4j_mcp")
    return exit_code


def format_code():
    """Format code."""
    return run_command("uv run ruff format .")


def server(args):
    """Run the MCP server."""
    cmd = "uv run neo4j-mcp-server"
    if args:
        cmd += " " + " ".join(args)
    return run_command(cmd)


def client(args):
    """Run the MCP client."""
    cmd = "uv run neo4j-mcp-client"
    if args:
        cmd += " " + " ".join(args)
    return run_command(cmd)


def dev_server():
    """Run server in development mode."""
    return run_command("uv run mcp dev src/neo4j_mcp/server.py")


def build():
    """Build the package."""
    return run_command("uv build")


def clean():
    """Clean build artifacts."""
    import shutil
    
    artifacts = [
        "dist",
        "build", 
        ".coverage",
        "htmlcov",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "*.egg-info"
    ]
    
    for artifact in artifacts:
        for path in Path(".").rglob(artifact):
            if path.exists():
                print(f"Removing {path}")
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
    
    return 0


def install():
    """Install the package in development mode."""
    return run_command("uv pip install -e .")


def docs():
    """Generate documentation (placeholder)."""
    print("Documentation generation not implemented yet")
    print("See README.md for usage instructions")
    return 0


def demo():
    """Run a quick demo."""
    print("🚀 Neo4j MCP Quick Demo")
    print("=" * 30)
    
    # Test connection with a simple query
    print("\n1. Testing connection...")
    exit_code = run_command('uv run neo4j-mcp-client --query "RETURN 1 as test"', capture_output=True)
    
    if exit_code == 0:
        print("✅ Connection successful!")
        
        print("\n2. Getting schema information...")
        run_command('uv run neo4j-mcp-client --query "CALL db.labels()"', capture_output=True)
        
        print("\n3. Counting nodes...")
        run_command('uv run neo4j-mcp-client --query "MATCH (n) RETURN count(n) as total_nodes"', capture_output=True)
        
    else:
        print("❌ Connection failed. Make sure Neo4j is running and configured properly.")
        print("Check your .env file or environment variables.")
    
    return exit_code


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Neo4j MCP development tasks")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup
    subparsers.add_parser("setup", help="Set up development environment")
    
    # Testing
    subparsers.add_parser("test", help="Run tests")
    subparsers.add_parser("test-cov", help="Run tests with coverage")
    
    # Code quality
    subparsers.add_parser("lint", help="Run linting")
    subparsers.add_parser("format", help="Format code")
    
    # Server/Client
    server_parser = subparsers.add_parser("server", help="Run MCP server")
    server_parser.add_argument("args", nargs="*", help="Additional server arguments")
    
    client_parser = subparsers.add_parser("client", help="Run MCP client")  
    client_parser.add_argument("args", nargs="*", help="Additional client arguments")
    
    subparsers.add_parser("dev-server", help="Run server in development mode")
    
    # Build/Install
    subparsers.add_parser("build", help="Build package")
    subparsers.add_parser("install", help="Install in development mode")
    subparsers.add_parser("clean", help="Clean build artifacts")
    
    # Docs
    subparsers.add_parser("docs", help="Generate documentation")
    
    # Demo
    subparsers.add_parser("demo", help="Run quick demo")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Map commands to functions
    commands = {
        "setup": setup_dev,
        "test": test,
        "test-cov": test_coverage,
        "lint": lint,
        "format": format_code,
        "server": lambda: server(args.args if hasattr(args, 'args') else []),
        "client": lambda: client(args.args if hasattr(args, 'args') else []),
        "dev-server": dev_server,
        "build": build,
        "install": install,
        "clean": clean,
        "docs": docs,
        "demo": demo,
    }
    
    if args.command in commands:
        return commands[args.command]()
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 