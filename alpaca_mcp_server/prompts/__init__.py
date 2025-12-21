"""Prompts module for Alpaca MCP Server - Guided trading workflows."""

# Import all prompt modules
from .account_analysis_prompt import account_analysis
from .finance_prompt import finance
from .list_trading_capabilities import list_trading_capabilities
from .market_analysis_prompt import market_analysis
from .market_overview_prompt import market_overview
from .position_management_prompt import position_management
from .scan_prompt import scan
from .sr_prompt import sr
from .startup_prompt import startup

__all__ = [
    "list_trading_capabilities",
    "account_analysis",
    "position_management",
    "market_analysis",
    "market_overview",
    "finance",
    "sr",
    "startup",
    "scan",
]

# Day trading workflow - complete agentic trading analysis
from .day_trading_workflow import day_trading_workflow
from .market_session_workflow import market_session_workflow
from .master_scanning_workflow import master_scanning_workflow
from .pro_technical_workflow import pro_technical_workflow
from .stream_centric_trading_prompt import (
    stream_centric_trading_cycle,
    stream_concurrent_monitoring_cycle,
)

__all__.extend(
    [
        "day_trading_workflow",
        "master_scanning_workflow",
        "pro_technical_workflow",
        "market_session_workflow",
        "stream_centric_trading_cycle",
        "stream_concurrent_monitoring_cycle",
    ]
)
