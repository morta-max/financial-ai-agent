"""
MCP Server configuration for AI tool integration.

To use with Claude Desktop, add to your claude_desktop_config.json:
{
  "mcpServers": {
    "a-share-finance": {
      "command": "python",
      "args": ["-m", "backend.mcp_server.server", "--transport", "stdio"],
      "cwd": "/path/to/financial-ai-agent"
    }
  }
}

To use with Cursor, add to .cursor/mcp.json:
{
  "mcpServers": {
    "a-share-finance": {
      "command": "python",
      "args": ["-m", "backend.mcp_server.server", "--transport", "stdio"],
      "cwd": "${workspaceFolder}"
    }
  }
}

To use with Windsurf, configure in settings.

To run as standalone HTTP server:
  python -m backend.mcp_server.server --transport http --port 8001
"""

import json
import os

# Configuration file path for AI tools
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)


def generate_claude_config() -> dict:
    """Generate Claude Desktop MCP configuration."""
    return {
        "mcpServers": {
            "a-share-finance": {
                "command": "python",
                "args": [
                    "-m", "backend.mcp_server.server",
                    "--transport", "stdio"
                ],
                "cwd": PROJECT_ROOT,
                "env": {
                    "DUCKDB_PATH": os.path.join(PROJECT_ROOT, "data", "financial_agent.duckdb"),
                }
            }
        }
    }


def generate_cursor_config() -> dict:
    """Generate Cursor MCP configuration."""
    return {
        "mcpServers": {
            "a-share-finance": {
                "command": "python",
                "args": [
                    "-m", "backend.mcp_server.server",
                    "--transport", "stdio"
                ],
                "cwd": "${workspaceFolder}",
            }
        }
    }


def print_configs():
    """Print configuration examples for various AI tools."""
    print("=" * 70)
    print("A-Share Financial Agent - MCP Configuration")
    print("=" * 70)

    print("\n--- Claude Desktop (claude_desktop_config.json) ---")
    print(json.dumps(generate_claude_config(), indent=2, ensure_ascii=False))

    print("\n--- Cursor (.cursor/mcp.json) ---")
    print(json.dumps(generate_cursor_config(), indent=2, ensure_ascii=False))

    print("\n--- Windsurf ---")
    print("Add in settings:")
    print(f"  Command: python")
    print(f"  Args: -m backend.mcp_server.server --transport stdio")
    print(f"  Working Directory: {PROJECT_ROOT}")

    print("\n--- HTTP Server ---")
    print(f"  python -m backend.mcp_server.server --transport http --port 8001")
    print(f"  Then connect to: http://localhost:8001/sse")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print_configs()
