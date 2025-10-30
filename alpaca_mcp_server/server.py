"""Main MCP server implementation with prompt-driven architecture."""

import os
import sys

# Handle both direct execution and module import
if __name__ == "__main__" or not __package__:
    # Add parent directory to path for direct execution
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from alpaca_mcp_server.config.settings import settings
    from alpaca_mcp_server.server_components import (
        register_all_prompts,
        register_all_resources,
        register_all_tools,
    )
    from alpaca_mcp_server.server_components.server_init import (
        apply_compatibility_patches,
        get_default_window_len,
        initialize_help_system,
    )
else:
    from .config.settings import settings
    from .server_components import (
        register_all_prompts,
        register_all_resources,
        register_all_tools,
    )
    from .server_components.server_init import (
        apply_compatibility_patches,
        get_default_window_len,
        initialize_help_system,
    )

from mcp.server.fastmcp import FastMCP

# Create the FastMCP server instance
mcp = FastMCP(
    name=settings.server_name,
    version=settings.version,
    dependencies=["alpaca-py>=0.40.1", "python-dotenv>=1.1.0"],
)

# Get global configuration values with error handling
DEFAULT_WINDOW_LEN = get_default_window_len()

# ============================================================================
# REGISTRATION - Register all components with the MCP server
# ============================================================================

# Register all prompts
register_all_prompts(mcp)

# Register all tools
register_all_tools(mcp, DEFAULT_WINDOW_LEN)

# Register all resources
register_all_resources(mcp)


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================


def get_server():
    """Get the MCP server instance."""
    # Apply Claude Code compatibility patches
    patched_mcp = apply_compatibility_patches(mcp)

    # Initialize help system after all tools and prompts are registered
    initialize_help_system(patched_mcp)

    return patched_mcp


def main() -> None:
    """Main entry point for the MCP server."""
    # Apply Claude Code compatibility patches
    server = apply_compatibility_patches(mcp)

    # Initialize help system after all tools and prompts are registered
    initialize_help_system(server)

    print("🚀 Starting MCP server...")
    server.run()


# ============================================================================
# MAIN EXECUTION - Apply Patches and Initialize Help System at End
# ============================================================================

if __name__ == "__main__":
    main()
