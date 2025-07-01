"""Server components for modular MCP server organization."""

from .prompt_registrations import register_all_prompts
from .resource_registrations import register_all_resources
from .tool_registrations import register_all_tools

__all__ = ["register_all_tools", "register_all_prompts", "register_all_resources"]
