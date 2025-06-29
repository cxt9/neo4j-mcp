#!/usr/bin/env python3
"""Development setup script for Neo4j MCP."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, cwd: Path = None) -> bool:
    """Run a shell command and return success status."""
    try:
        print(f"Running: {cmd}")
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=True, 
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True


def check_uv():
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("✅ uv is already installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  uv is not installed")
        return False


def install_uv():
    """Install uv package manager."""
    print("Installing uv...")
    
    # Try different installation methods
    methods = [
        "pip install uv",
        "pipx install uv",
        "curl -LsSf https://astral.sh/uv/install.sh | sh"
    ]
    
    for method in methods:
        print(f"Trying: {method}")
        if run_command(method):
            print("✅ uv installed successfully")
            return True
    
    print("❌ Failed to install uv. Please install manually:")
    print("https://github.com/astral-sh/uv#installation")
    return False


def setup_project():
    """Set up the project dependencies."""
    project_root = Path(__file__).parent
    
    print("\n📦 Setting up project dependencies...")
    
    # Install dependencies with uv
    if not run_command("uv sync", cwd=project_root):
        print("❌ Failed to install dependencies with uv")
        print("Trying with pip...")
        if not run_command("pip install -e .", cwd=project_root):
            return False
    
    print("✅ Dependencies installed successfully")
    return True


def create_env_file():
    """Create a .env file if it doesn't exist."""
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    env_example = project_root / "examples" / "env_example.txt"
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if env_example.exists():
        print("📝 Creating .env file from example...")
        try:
            with open(env_example, 'r') as src:
                content = src.read()
            
            with open(env_file, 'w') as dst:
                dst.write(content)
            
            print("✅ .env file created")
            print("📝 Please edit .env file with your Neo4j connection details")
            return True
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    else:
        print("⚠️  No example .env file found")
        return True


def test_installation():
    """Test the installation by running basic commands."""
    print("\n🧪 Testing installation...")
    
    # Test importing the package
    try:
        import neo4j_mcp
        print("✅ Package imports successfully")
    except ImportError as e:
        print(f"❌ Failed to import package: {e}")
        return False
    
    # Test server command
    try:
        result = subprocess.run(
            ["neo4j-mcp-server", "--help"], 
            check=True, 
            capture_output=True,
            timeout=10
        )
        print("✅ neo4j-mcp-server command works")
    except Exception as e:
        print(f"⚠️  neo4j-mcp-server command test failed: {e}")
        print("This might be expected if Neo4j is not running")
    
    # Test client command
    try:
        result = subprocess.run(
            ["neo4j-mcp-client", "--help"], 
            check=True, 
            capture_output=True,
            timeout=10
        )
        print("✅ neo4j-mcp-client command works")
    except Exception as e:
        print(f"⚠️  neo4j-mcp-client command test failed: {e}")
    
    return True


def print_next_steps():
    """Print next steps for the user."""
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("1. Edit the .env file with your Neo4j connection details")
    print("2. Make sure Neo4j is running (local or cloud)")
    print("3. Test the connection:")
    print("   neo4j-mcp-client --query 'RETURN 1 as test'")
    print("4. Start the MCP server:")
    print("   neo4j-mcp-server")
    print("5. Configure your LLM (Claude Desktop, Cursor, etc.) with the server")
    print("\n📖 Documentation:")
    print("   - README.md for detailed usage instructions")
    print("   - examples/ directory for configuration examples")
    print("   - examples/queries/ for sample Cypher queries")


def main():
    """Main setup function."""
    print("🚀 Neo4j MCP Development Setup")
    print("=" * 40)
    
    # Check requirements
    if not check_python_version():
        sys.exit(1)
    
    # Install uv if needed
    if not check_uv():
        if not install_uv():
            print("\n❌ Setup failed: Could not install uv")
            sys.exit(1)
    
    # Set up project
    if not setup_project():
        print("\n❌ Setup failed: Could not install dependencies")
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Test installation
    if not test_installation():
        print("\n⚠️  Some tests failed, but setup might still work")
    
    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    main() 