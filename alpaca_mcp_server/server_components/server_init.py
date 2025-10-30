"""Server initialization module for MCP server."""

import os
import sys


def handle_imports() -> None:
    """Handle import path configuration for direct execution."""
    if __name__ == "__main__" or not __package__:
        # Add parent directory to path for direct execution
        sys.path.insert(
            0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )


def get_default_window_len():
    """Get global configuration values with error handling."""
    from ..config import get_technical_config

    try:
        technical_config = get_technical_config()
        window_len = technical_config.hanning_window_samples
        print(f"✅ Configuration loaded successfully - Window length: {window_len}")
        return window_len
    except Exception as e:
        print(f"⚠️ Config loading failed: {e}, using defaults")
        return 11


def apply_compatibility_patches(mcp):
    """Apply Claude Code compatibility patches."""
    print("🔧 Applying Claude Code MCP compatibility patches...")

    from ..claude_code_tool_fix import (
        add_claude_code_debug_tools,
        apply_claude_code_tool_registration_fix,
        force_claude_code_protocol_compliance,
    )
    from ..compatibility import apply_claude_code_compatibility

    _compatibility_patch = apply_claude_code_compatibility(mcp)
    mcp = apply_claude_code_tool_registration_fix(mcp)
    mcp = force_claude_code_protocol_compliance(mcp)
    mcp = add_claude_code_debug_tools(mcp)

    return mcp


def initialize_help_system(mcp):
    """Initialize help system after all tools and prompts are registered."""
    print("📚 Initializing help system...")
    from ..resources import help_system

    help_system.initialize_help_system(mcp)
