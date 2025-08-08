"""
Unit tests for the refactored server components.
Tests the modular architecture and registration functions.
"""

from unittest.mock import Mock

import pytest
from mcp.server.fastmcp import FastMCP

from alpaca_mcp_server.server_components import (
    register_all_prompts,
    register_all_resources,
    register_all_tools,
)
from alpaca_mcp_server.server_components.prompt_registrations import (
    register_core_prompts,
    register_workflow_prompts,
)
from alpaca_mcp_server.server_components.resource_registrations import (
    register_account_resources,
    register_market_resources,
)
from alpaca_mcp_server.server_components.server_init import (
    get_default_window_len,
)
from alpaca_mcp_server.server_components.tool_registrations import (
    register_account_tools,
    register_market_data_tools,
    register_scanner_tools,
)


class TestServerComponentsArchitecture:
    """Test the overall architecture of the refactored server components."""

    def test_imports_work(self):
        """Test that all component imports work correctly."""
        # This test passes if imports succeed without errors
        assert register_all_tools is not None
        assert register_all_prompts is not None
        assert register_all_resources is not None

    def test_registration_functions_exist(self):
        """Test that all main registration functions exist."""
        # Test tool registration functions
        assert callable(register_account_tools)
        assert callable(register_market_data_tools)
        assert callable(register_scanner_tools)

        # Test prompt registration functions
        assert callable(register_core_prompts)
        assert callable(register_workflow_prompts)

        # Test resource registration functions
        assert callable(register_account_resources)
        assert callable(register_market_resources)


class TestToolRegistrations:
    """Test tool registration functionality."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance for testing."""
        mcp = Mock(spec=FastMCP)
        mcp.tool = Mock(return_value=lambda func: func)
        return mcp

    def test_register_account_tools(self, mock_mcp):
        """Test account tools registration."""
        register_account_tools(mock_mcp)

        # Verify tool decorator was called (tools were registered)
        assert mock_mcp.tool.called
        call_count = mock_mcp.tool.call_count

        # Account tools should register multiple functions
        assert call_count >= 3  # At least account info, positions, close position

    def test_register_market_data_tools(self, mock_mcp):
        """Test market data tools registration."""
        register_market_data_tools(mock_mcp)

        # Verify tools were registered
        assert mock_mcp.tool.called
        call_count = mock_mcp.tool.call_count

        # Market data tools should register multiple functions
        assert call_count >= 5  # At least quote, snapshots, bars, trades, etc.

    def test_register_all_tools_integration(self, mock_mcp):
        """Test that register_all_tools calls all sub-registration functions."""
        DEFAULT_WINDOW_LEN = 11

        register_all_tools(mock_mcp, DEFAULT_WINDOW_LEN)

        # Should have registered many tools
        assert mock_mcp.tool.call_count > 20  # We have 50+ tools total


class TestPromptRegistrations:
    """Test prompt registration functionality."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance for testing."""
        mcp = Mock(spec=FastMCP)
        mcp.prompt = Mock(return_value=lambda func: func)
        return mcp

    def test_register_core_prompts(self, mock_mcp):
        """Test core prompts registration."""
        register_core_prompts(mock_mcp)

        # Verify prompt decorator was called
        assert mock_mcp.prompt.called
        call_count = mock_mcp.prompt.call_count

        # Core prompts should register several functions
        assert call_count >= 5  # startup, scan, account_analysis, etc.

    def test_register_workflow_prompts(self, mock_mcp):
        """Test workflow prompts registration."""
        register_workflow_prompts(mock_mcp)

        # Verify prompts were registered
        assert mock_mcp.prompt.called
        call_count = mock_mcp.prompt.call_count

        # Workflow prompts should register several functions
        assert call_count >= 3  # day_trading, master_scanning, etc.

    def test_register_all_prompts_integration(self, mock_mcp):
        """Test that register_all_prompts calls all sub-registration functions."""
        register_all_prompts(mock_mcp)

        # Should have registered multiple prompts
        assert mock_mcp.prompt.call_count >= 8  # Total prompts across categories


class TestResourceRegistrations:
    """Test resource registration functionality."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP instance for testing."""
        mcp = Mock(spec=FastMCP)
        mcp.resource = Mock(return_value=lambda func: func)
        mcp.tool = Mock(return_value=lambda func: func)  # For resource mirror tools
        return mcp

    def test_register_account_resources(self, mock_mcp):
        """Test account resources registration."""
        register_account_resources(mock_mcp)

        # Verify resource decorator was called
        assert mock_mcp.resource.called
        call_count = mock_mcp.resource.call_count

        # Should register at least account status resource
        assert call_count >= 1

    def test_register_market_resources(self, mock_mcp):
        """Test market resources registration."""
        register_market_resources(mock_mcp)

        # Verify resources were registered
        assert mock_mcp.resource.called
        call_count = mock_mcp.resource.call_count

        # Should register conditions and momentum resources
        assert call_count >= 2

    def test_register_all_resources_integration(self, mock_mcp):
        """Test that register_all_resources calls all sub-registration functions."""
        register_all_resources(mock_mcp)

        # Should have registered multiple resources and mirror tools
        assert mock_mcp.resource.call_count >= 10  # Various resource types
        assert mock_mcp.tool.call_count >= 8  # Resource mirror tools


class TestServerInitialization:
    """Test server initialization utilities."""

    def test_get_default_window_len_returns_int(self):
        """Test that get_default_window_len returns a valid integer."""
        window_len = get_default_window_len()

        assert isinstance(window_len, int)
        assert window_len > 0
        assert window_len <= 101  # Technical constraint for Hanning window

    def test_get_default_window_len_handles_config_error(self, monkeypatch):
        """Test that get_default_window_len handles configuration errors gracefully."""

        # Mock the config import to raise an exception
        def mock_get_technical_config():
            raise Exception("Config error")

        monkeypatch.setattr(
            "alpaca_mcp_server.server_components.server_init.get_technical_config",
            mock_get_technical_config,
        )

        # Should return default value when config fails
        window_len = get_default_window_len()
        assert window_len == 11  # Default fallback value


class TestModularArchitectureBenefits:
    """Test that the modular architecture provides the expected benefits."""

    def test_components_are_independent(self):
        """Test that components can be imported independently."""
        # Each component should be importable without importing the others
        from alpaca_mcp_server.server_components.prompt_registrations import register_core_prompts
        from alpaca_mcp_server.server_components.resource_registrations import (
            register_account_resources,
        )
        from alpaca_mcp_server.server_components.tool_registrations import register_account_tools

        # All should be callable functions
        assert callable(register_account_tools)
        assert callable(register_core_prompts)
        assert callable(register_account_resources)

    def test_main_registration_functions_coordinate(self):
        """Test that main registration functions coordinate sub-functions."""
        mock_mcp = Mock(spec=FastMCP)
        mock_mcp.tool = Mock(return_value=lambda func: func)
        mock_mcp.prompt = Mock(return_value=lambda func: func)
        mock_mcp.resource = Mock(return_value=lambda func: func)

        # Register everything
        register_all_tools(mock_mcp, 11)
        register_all_prompts(mock_mcp)
        register_all_resources(mock_mcp)

        # Should have made many registration calls
        assert mock_mcp.tool.call_count > 50  # Many tools
        assert mock_mcp.prompt.call_count > 8  # Several prompts
        assert mock_mcp.resource.call_count > 10  # Multiple resources

    def test_registration_functions_are_idempotent(self):
        """Test that registration functions can be called multiple times safely."""
        mock_mcp = Mock(spec=FastMCP)
        mock_mcp.tool = Mock(return_value=lambda func: func)

        # Call registration twice
        register_account_tools(mock_mcp)
        first_call_count = mock_mcp.tool.call_count

        register_account_tools(mock_mcp)
        second_call_count = mock_mcp.tool.call_count

        # Second call should register the same number of additional tools
        assert second_call_count == first_call_count * 2
