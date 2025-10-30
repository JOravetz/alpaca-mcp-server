"""Claude Code specific tool registration fixes."""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def apply_claude_code_tool_registration_fix(mcp: Any) -> Any:
    """Apply fixes to ensure tools are properly registered for Claude Code.

    Claude Code has specific requirements for tool discovery that differ
    from standard MCP servers.
    """
    # Enable debug mode if requested
    if os.getenv("CLAUDE_CODE_TOOL_DISCOVERY") == "1":
        logger.info("Claude Code tool discovery mode enabled")
        print("🔧 Applying Claude Code tool registration fixes...")

    # FastMCP stores tools differently
    if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
        tool_count = len(mcp._tool_manager._tools)
        print(f"📦 Found {tool_count} tools in FastMCP tool manager")

        # Ensure all tools have proper metadata
        for tool_name, tool_data in mcp._tool_manager._tools.items():
            if (
                hasattr(tool_data, "func")
                and tool_data.func
                and (not hasattr(tool_data.func, "__doc__") or not tool_data.func.__doc__)
            ):
                tool_data.func.__doc__ = f"Tool function: {tool_name}"
    elif hasattr(mcp, "_tools"):
        # Legacy format
        for tool_name, tool_func in mcp._tools.items():
            if not hasattr(tool_func, "__doc__") or not tool_func.__doc__:
                tool_func.__doc__ = f"Tool function: {tool_name}"
    else:
        print("⚠️  No tools found to register")

    return mcp


def force_claude_code_protocol_compliance(mcp: Any) -> Any:
    """Force the server to comply with Claude Code's specific protocol requirements."""
    # Claude Code expects certain response formats
    if hasattr(mcp, "_server") and hasattr(mcp._server, "capabilities"):
        # Ensure proper capability advertisement
        mcp._server.capabilities["tools"] = {"listChanged": True}
        mcp._server.capabilities["prompts"] = {"listChanged": True}
        mcp._server.capabilities["resources"] = {"subscribe": True}

    return mcp


def add_claude_code_debug_tools(mcp: Any) -> Any:
    """Add debug tools specifically for Claude Code integration testing."""

    @mcp.tool()
    async def debug_list_tools() -> dict[str, Any]:
        """Debug tool to list all registered tools in the MCP server."""
        if hasattr(mcp, "_tools"):
            return {
                "tool_count": len(mcp._tools),
                "tools": list(mcp._tools.keys()),
                "message": f"Found {len(mcp._tools)} tools registered",
            }
        return {"error": "No tools found", "tool_count": 0}

    @mcp.tool()
    async def debug_server_info() -> dict[str, Any]:
        """Debug tool to get MCP server information."""
        info = {
            "server_name": getattr(mcp, "name", "unknown"),
            "version": getattr(mcp, "version", "unknown"),
            "has_tools": hasattr(mcp, "_tools"),
            "has_prompts": hasattr(mcp, "_prompts"),
            "has_resources": hasattr(mcp, "_resources"),
        }

        if hasattr(mcp, "_tools"):
            info["tool_count"] = len(mcp._tools)
        if hasattr(mcp, "_prompts"):
            info["prompt_count"] = len(mcp._prompts)
        if hasattr(mcp, "_resources"):
            info["resource_count"] = len(mcp._resources)

        return info

    return mcp
