#!/usr/bin/env python3
"""Comprehensive tool architecture analysis for MCP server."""

import ast
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple


def analyze_tool_file(file_path: Path) -> Dict:
    """Analyze a single tool file for architecture patterns."""
    content = file_path.read_text()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"error": f"Syntax error in {file_path}"}

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            # Get function details
            lines = node.end_lineno - node.lineno if node.end_lineno else 0
            docstring = ast.get_docstring(node) or ""

            # Check if it's a tool (async function)
            is_tool = node.name.startswith("get_") or node.name.startswith("scan_") or node.name.startswith("place_") or node.name.startswith("analyze_")

            # Count internal complexity
            has_loops = any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(node))
            has_conditionals = sum(1 for n in ast.walk(node) if isinstance(n, ast.If))
            has_try_except = sum(1 for n in ast.walk(node) if isinstance(n, ast.Try))

            # Check for external calls (composition)
            has_client_calls = "client." in ast.unparse(node) if hasattr(ast, 'unparse') else False

            functions.append({
                "name": node.name,
                "lines": lines,
                "docstring_length": len(docstring),
                "has_docstring": bool(docstring),
                "is_tool": is_tool,
                "complexity": has_conditionals + (2 if has_loops else 0),
                "error_handling": has_try_except,
                "is_composite": has_client_calls
            })

    return {
        "file": file_path.name,
        "functions": functions,
        "total_lines": len(content.splitlines())
    }


def categorize_tools(tools_dir: Path) -> Dict:
    """Categorize all tools by type and complexity."""

    categories = {
        "scanners": [],
        "data_fetchers": [],
        "order_management": [],
        "analysis": [],
        "monitoring": [],
        "plotting": [],
        "other": []
    }

    primitives = []
    composites = []
    large_tools = []
    missing_docstrings = []

    for tool_file in tools_dir.glob("*.py"):
        if tool_file.name.startswith("__"):
            continue

        analysis = analyze_tool_file(tool_file)

        if "error" in analysis:
            continue

        for func in analysis["functions"]:
            if not func["is_tool"]:
                continue

            tool_info = {
                "file": tool_file.name,
                "name": func["name"],
                "lines": func["lines"],
                "complexity": func["complexity"]
            }

            # Categorize by name pattern
            if "scan" in func["name"]:
                categories["scanners"].append(tool_info)
            elif func["name"].startswith("get_"):
                categories["data_fetchers"].append(tool_info)
            elif func["name"].startswith("place_") or "order" in func["name"]:
                categories["order_management"].append(tool_info)
            elif "analyze" in func["name"] or "peak" in func["name"]:
                categories["analysis"].append(tool_info)
            elif "monitor" in func["name"] or "stream" in func["name"]:
                categories["monitoring"].append(tool_info)
            elif "plot" in func["name"] or "chart" in func["name"]:
                categories["plotting"].append(tool_info)
            else:
                categories["other"].append(tool_info)

            # Track composition and size
            if func["is_composite"]:
                composites.append(tool_info)
            else:
                primitives.append(tool_info)

            if func["lines"] > 100:
                large_tools.append(tool_info)

            if not func["has_docstring"] or func["docstring_length"] < 50:
                missing_docstrings.append(tool_info)

    return {
        "categories": categories,
        "primitives": primitives,
        "composites": composites,
        "large_tools": large_tools,
        "missing_docstrings": missing_docstrings
    }


def print_analysis(analysis: Dict):
    """Print comprehensive analysis report."""

    print("=" * 80)
    print("MCP SERVER TOOL ARCHITECTURE ANALYSIS")
    print("=" * 80)

    # Category breakdown
    print("\n📊 TOOL CATEGORIES:")
    for category, tools in analysis["categories"].items():
        if tools:
            print(f"\n  {category.upper()}: {len(tools)} tools")
            for tool in sorted(tools, key=lambda x: x["lines"], reverse=True)[:3]:
                print(f"    - {tool['name']}: {tool['lines']} lines (complexity: {tool['complexity']})")

    # Composition analysis
    print("\n" + "=" * 80)
    print("🔧 COMPOSITION ANALYSIS:")
    print(f"  Primitive tools: {len(analysis['primitives'])}")
    print(f"  Composite tools: {len(analysis['composites'])}")
    print(f"  Composition ratio: {len(analysis['composites']) / max(1, len(analysis['primitives']) + len(analysis['composites'])):.1%}")

    # Large tools that need breaking down
    print("\n" + "=" * 80)
    print("⚠️  LARGE TOOLS (>100 lines - consider breaking down):")
    for tool in sorted(analysis["large_tools"], key=lambda x: x["lines"], reverse=True)[:10]:
        print(f"  - {tool['name']}: {tool['lines']} lines ({tool['file']})")

    # Documentation issues
    print("\n" + "=" * 80)
    print("📝 DOCUMENTATION ISSUES (missing or weak docstrings):")
    for tool in analysis["missing_docstrings"][:15]:
        print(f"  - {tool['name']} ({tool['file']})")

    # Scanner consolidation opportunities
    print("\n" + "=" * 80)
    print("🔍 SCANNER CONSOLIDATION OPPORTUNITIES:")
    scanners = analysis["categories"]["scanners"]
    if scanners:
        print(f"  Total scanners: {len(scanners)}")
        print("  Scanner tools:")
        for scanner in scanners:
            print(f"    - {scanner['name']} ({scanner['lines']} lines)")
        print("\n  💡 RECOMMENDATION: Consolidate into 2-3 core scanners with strategy parameters")

    # Summary stats
    print("\n" + "=" * 80)
    print("📈 SUMMARY STATISTICS:")
    total_tools = sum(len(tools) for tools in analysis["categories"].values())
    avg_lines = sum(t["lines"] for cat in analysis["categories"].values() for t in cat) / max(1, total_tools)
    print(f"  Total tools: {total_tools}")
    print(f"  Average tool size: {avg_lines:.1f} lines")
    print(f"  Tools needing refactoring: {len(analysis['large_tools'])} (>100 lines)")
    print(f"  Tools needing better docs: {len(analysis['missing_docstrings'])}")
    print("=" * 80)


def main():
    tools_dir = Path("alpaca_mcp_server/tools")

    if not tools_dir.exists():
        print(f"Error: {tools_dir} not found")
        return

    analysis = categorize_tools(tools_dir)
    print_analysis(analysis)

    # Export detailed data for further analysis
    import json
    with open("tool_architecture_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    print("\n✅ Detailed analysis saved to tool_architecture_analysis.json")


if __name__ == "__main__":
    main()
