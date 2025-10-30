#!/usr/bin/env python3
"""Entry point for the Alpaca MCP Server with prompt-driven architecture."""

import os
import sys

# Add parent directory to Python path for module resolution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    """Run the Alpaca MCP server."""
    try:
        print("🚀 Starting Alpaca Trading MCP Server...")
        print("📊 Prompt-driven architecture enabled")
        print("💡 Use list_trading_capabilities() to explore features")

        if __name__ == "__main__" or not __package__:
            from alpaca_mcp_server.server import mcp
        else:
            from .server import mcp
        mcp.run()
    except KeyboardInterrupt:
        print("\n⏹️ Alpaca MCP Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
