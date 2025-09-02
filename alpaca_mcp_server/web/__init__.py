"""Web services for MCP server.

This module provides web-based interfaces for the MCP server:
- MCP Execution Service: REST API for executing tools, resources, and prompts
"""

from .mcp_execution_service import app as mcp_execution_app

__all__ = ["mcp_execution_app"]