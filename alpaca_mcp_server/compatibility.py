"""Claude Code MCP compatibility layer."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def apply_claude_code_compatibility(mcp: Any) -> Any:
    """Apply Claude Code specific compatibility patches to the MCP server.

    This ensures proper tool discovery and registration for Claude Code.
    """
    # Check if Claude Code mode is enabled
    claude_code_mode = os.getenv("CLAUDE_CODE_TOOL_DISCOVERY") == "1"
    if claude_code_mode:
        logger.info("Claude Code compatibility mode ENABLED")
        print("✅ Claude Code compatibility mode ENABLED")
    else:
        logger.info("Claude Code compatibility mode disabled")
        print("⚠️  Claude Code compatibility mode disabled")

    # For now, just log the state - actual patching will happen after tools are registered
    if hasattr(mcp, "_tool_manager"):
        # This will be 0 initially since tools haven't been registered yet
        print("🔧 FastMCP tool manager initialized (tools will be registered later)")

    # Add a flag to indicate Claude Code mode
    mcp._claude_code_mode = claude_code_mode

    return mcp
