"""
Help System Resource - Auto-generated tool documentation and introspection
"""

import inspect
from typing import Any

from mcp.server.fastmcp import FastMCP


class HelpSystem:
    """
    Comprehensive help system for MCP tools with auto-generation and introspection.

    Features:
    - Auto-extracts function signatures and docstrings
    - Provides usage examples and parameter details
    - Supports batch help for all tools
    - CLI-style --help integration
    """

    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        self._tool_registry: dict[str, Any] = {}
        self._prompt_registry: dict[str, Any] = {}
        self._resource_registry: dict[str, Any] = {}
        self._build_registries()

    def _build_registries(self):
        """Build comprehensive registries of all MCP components."""
        # Note: FastMCP tools are registered lazily, so this might be empty initially
        # We'll rebuild registries on demand in get_* methods
        self._update_tool_registry()
        self._update_prompt_registry()
        self._update_resource_registry()

    def _update_tool_registry(self):
        """Update tool registry from current server state."""
        # FastMCP stores tools in _tool_manager._tools
        if hasattr(self.mcp_server, "_tool_manager") and hasattr(
            self.mcp_server._tool_manager, "_tools"
        ):
            tools = self.mcp_server._tool_manager._tools
            for tool_name, tool_obj in tools.items():
                if tool_name not in self._tool_registry:
                    self._tool_registry[tool_name] = self._extract_fastmcp_tool_info(
                        tool_name, tool_obj
                    )

    def _update_prompt_registry(self):
        """Update prompt registry from current server state."""
        # FastMCP stores prompts in _prompt_manager._prompts
        if hasattr(self.mcp_server, "_prompt_manager") and hasattr(
            self.mcp_server._prompt_manager, "_prompts"
        ):
            prompts = self.mcp_server._prompt_manager._prompts
            for prompt_name, prompt_obj in prompts.items():
                if prompt_name not in self._prompt_registry:
                    self._prompt_registry[prompt_name] = self._extract_fastmcp_prompt_info(
                        prompt_name, prompt_obj
                    )

    def _update_resource_registry(self):
        """Update resource registry from current server state."""
        if hasattr(self.mcp_server, "_resources") and self.mcp_server._resources:
            for resource_name, resource_info in self.mcp_server._resources.items():
                if resource_name not in self._resource_registry:
                    self._resource_registry[resource_name] = self._extract_resource_info(
                        resource_name, resource_info
                    )

    def _extract_fastmcp_tool_info(self, tool_name: str, tool_obj: Any) -> dict[str, Any]:
        """Extract comprehensive information about a FastMCP tool object."""
        try:
            # FastMCP tool object has: fn, name, description, parameters, fn_metadata, is_async, context_kwarg, annotations
            func = tool_obj.fn
            description = tool_obj.description or "No description available"

            # FastMCP already provides JSON Schema parameters
            input_schema = {
                "type": "object",
                "properties": tool_obj.parameters.get("properties", {}),
                "required": tool_obj.parameters.get("required", []),
            }

            # Extract annotations from FastMCP tool object or generate them
            annotations = tool_obj.annotations or {}
            if not annotations:
                annotations = self._generate_tool_annotations(tool_name, description)

            # Convert to our format
            return {
                "name": tool_name,
                "type": "tool",
                "description": description,
                "full_description": inspect.getdoc(func) or description,
                "input_schema": input_schema,
                "annotations": annotations,
                "return_type": "str",  # FastMCP tools typically return strings
                "usage_examples": self._generate_usage_examples(
                    tool_name, input_schema.get("properties", {})
                ),
                "related_tools": self._find_related_tools(tool_name),
                "category": self._categorize_tool(tool_name),
                # Legacy format for backward compatibility
                "parameters": self._convert_schema_to_legacy_params(
                    input_schema.get("properties", {}), input_schema.get("required", [])
                ),
            }

        except Exception as e:
            return {
                "name": tool_name,
                "type": "tool",
                "description": f"Error extracting FastMCP tool info: {str(e)}",
                "input_schema": {"type": "object", "properties": {}},
                "annotations": {},
                "parameters": {},
                "error": str(e),
            }

    def _extract_fastmcp_prompt_info(self, prompt_name: str, prompt_obj: Any) -> dict[str, Any]:
        """Extract information about a FastMCP prompt object."""
        try:
            func = prompt_obj.fn
            description = prompt_obj.description or "No description available"

            # Get function signature for parameters
            sig = inspect.signature(func)
            parameters = {}

            for param_name, param in sig.parameters.items():
                param_type = self._python_type_to_json_schema(param.annotation)
                param_description = self._extract_param_description(description, param_name)

                parameters[param_name] = {
                    "type": param_type,
                    "description": param_description,
                    "required": param.default == inspect.Parameter.empty,
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                }

            return {
                "name": prompt_name,
                "type": "prompt",
                "description": description,
                "full_description": inspect.getdoc(func) or description,
                "parameters": parameters,
                "usage_examples": self._generate_prompt_examples(prompt_name, parameters),
                "category": "workflow",
            }

        except Exception as e:
            return {
                "name": prompt_name,
                "type": "prompt",
                "description": f"Error extracting FastMCP prompt info: {str(e)}",
                "parameters": {},
                "error": str(e),
            }

    def _extract_tool_info(self, tool_name: str, tool_info: Any) -> dict[str, Any]:
        """Extract comprehensive information about a tool following MCP specification."""
        try:
            func = tool_info.get("func") if isinstance(tool_info, dict) else tool_info

            # Get function signature
            if func is None:
                return {
                    "name": tool_name,
                    "description": "Tool function not found",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            sig = inspect.signature(func)

            # Extract docstring
            docstring = inspect.getdoc(func) or "No description available"

            # Parse parameters for JSON Schema format (MCP standard)
            json_schema_properties = {}
            required_params = []

            for param_name, param in sig.parameters.items():
                # Skip 'help' parameter for our help system
                if param_name == "help":
                    continue

                param_type = self._python_type_to_json_schema(param.annotation)
                param_description = self._extract_param_description(docstring, param_name)

                json_schema_properties[param_name] = {
                    "type": param_type,
                    "description": param_description,
                }

                if param.default == inspect.Parameter.empty:
                    required_params.append(param_name)
                else:
                    # Add default value to schema
                    json_schema_properties[param_name]["default"] = param.default

            # Create MCP-compliant input schema
            input_schema = {
                "type": "object",
                "properties": json_schema_properties,
                "required": required_params,
            }

            # Determine annotations based on tool analysis
            annotations = self._generate_tool_annotations(tool_name, docstring)

            # Get return type
            return_type = (
                str(sig.return_annotation)
                if sig.return_annotation != inspect.Parameter.empty
                else "str"
            )

            return {
                "name": tool_name,
                "type": "tool",
                "description": (
                    docstring.split("\n")[0] if docstring else "No description available"
                ),
                "full_description": docstring,
                "input_schema": input_schema,
                "annotations": annotations,
                "return_type": return_type,
                "usage_examples": self._generate_usage_examples(tool_name, json_schema_properties),
                "related_tools": self._find_related_tools(tool_name),
                "category": self._categorize_tool(tool_name),
                # Legacy format for backward compatibility
                "parameters": self._convert_schema_to_legacy_params(
                    json_schema_properties, required_params
                ),
            }

        except Exception as e:
            return {
                "name": tool_name,
                "type": "tool",
                "description": f"Error extracting tool info: {str(e)}",
                "input_schema": {"type": "object", "properties": {}},
                "annotations": {},
                "parameters": {},
                "error": str(e),
            }

    def _python_type_to_json_schema(self, python_type) -> str:
        """Convert Python type annotations to JSON Schema types."""
        if python_type == inspect.Parameter.empty:
            return "string"  # Default to string

        type_str = str(python_type).lower()

        if "str" in type_str:
            return "string"
        elif "int" in type_str:
            return "integer"
        elif "float" in type_str:
            return "number"
        elif "bool" in type_str:
            return "boolean"
        elif "list" in type_str or "array" in type_str:
            return "array"
        elif "dict" in type_str or "object" in type_str:
            return "object"
        else:
            return "string"  # Default fallback

    def _generate_tool_annotations(self, tool_name: str, docstring: str) -> dict[str, Any]:
        """Generate MCP-compliant tool annotations based on tool analysis."""
        annotations: dict[str, Any] = {
            "title": self._generate_human_title(tool_name),
        }

        # Analyze tool behavior from name and description
        name_lower = tool_name.lower()
        # doc_lower = docstring.lower() if docstring else ""  # Currently unused

        # Determine if tool is read-only
        read_only_indicators = [
            "get_",
            "list_",
            "scan_",
            "search_",
            "analyze_",
            "check_",
            "validate_",
        ]
        write_indicators = [
            "place_",
            "cancel_",
            "close_",
            "create_",
            "delete_",
            "update_",
            "set_",
        ]

        if any(name_lower.startswith(indicator) for indicator in read_only_indicators):
            annotations["readOnlyHint"] = True
        elif any(name_lower.startswith(indicator) for indicator in write_indicators):
            annotations["readOnlyHint"] = False

        # Determine if tool is destructive
        destructive_indicators = ["cancel_", "close_", "delete_", "clear_"]
        if any(name_lower.startswith(indicator) for indicator in destructive_indicators):
            annotations["destructiveHint"] = True

        # Determine if tool involves external entities (open world)
        if any(word in name_lower for word in ["market", "stock", "order", "position", "stream"]):
            annotations["openWorldHint"] = True
        else:
            annotations["openWorldHint"] = False

        # Determine idempotency
        idempotent_indicators = ["get_", "list_", "scan_", "check_", "validate_"]
        if any(name_lower.startswith(indicator) for indicator in idempotent_indicators):
            annotations["idempotentHint"] = True

        return annotations

    def _generate_human_title(self, tool_name: str) -> str:
        """Generate a human-readable title from tool name."""
        # Convert snake_case to Title Case
        words = tool_name.split("_")
        return " ".join(word.capitalize() for word in words)

    def _convert_schema_to_legacy_params(
        self, properties: dict, required: list[str]
    ) -> dict[str, Any]:
        """Convert JSON Schema properties to legacy parameter format for backward compatibility."""
        legacy_params = {}
        for param_name, param_schema in properties.items():
            legacy_params[param_name] = {
                "name": param_name,
                "type": param_schema.get("type", "string"),
                "required": param_name in required,
                "default": param_schema.get("default"),
                "description": param_schema.get("description", "No description available"),
            }
        return legacy_params

    def _extract_prompt_info(self, prompt_name: str, prompt_info: Any) -> dict[str, Any]:
        """Extract information about a prompt/workflow."""
        try:
            func = prompt_info.get("func") if isinstance(prompt_info, dict) else prompt_info
            if func is None:
                return {"name": prompt_name, "description": "Prompt function not found"}
            sig = inspect.signature(func)
            docstring = inspect.getdoc(func) or "No description available"

            parameters = {}
            for param_name, param in sig.parameters.items():
                param_info = {
                    "name": param_name,
                    "type": (
                        str(param.annotation)
                        if param.annotation != inspect.Parameter.empty
                        else "Any"
                    ),
                    "required": param.default == inspect.Parameter.empty,
                    "default": (
                        str(param.default) if param.default != inspect.Parameter.empty else None
                    ),
                    "description": self._extract_param_description(docstring, param_name),
                }
                parameters[param_name] = param_info

            return {
                "name": prompt_name,
                "type": "prompt",
                "description": (
                    docstring.split("\n")[0] if docstring else "No description available"
                ),
                "full_description": docstring,
                "parameters": parameters,
                "usage_examples": self._generate_prompt_examples(prompt_name, parameters),
                "category": "workflow",
            }

        except Exception as e:
            return {
                "name": prompt_name,
                "type": "prompt",
                "description": f"Error extracting prompt info: {str(e)}",
                "parameters": {},
                "error": str(e),
            }

    def _extract_resource_info(self, resource_name: str, resource_info: Any) -> dict[str, Any]:
        """Extract information about a resource."""
        return {
            "name": resource_name,
            "type": "resource",
            "description": f"Real-time resource: {resource_name}",
            "category": "resource",
        }

    def _extract_param_description(self, docstring: str, param_name: str) -> str:
        """Extract parameter description from docstring."""
        if not docstring:
            return "No description available"

        lines = docstring.split("\n")
        for i, line in enumerate(lines):
            if param_name in line and (
                "Args:" in lines[max(0, i - 5) : i] or "Parameters:" in lines[max(0, i - 5) : i]
            ):
                # Try to extract description after parameter name
                if ":" in line:
                    return line.split(":", 1)[1].strip()

        return "No description available"

    def _generate_usage_examples(self, tool_name: str, parameters: dict[str, Any]) -> list[str]:
        """Generate usage examples for a tool (handles both formats)."""
        examples = []

        # Basic usage
        if not parameters:
            examples.append(f"{tool_name}()")
            return examples

        # Handle different parameter formats
        if isinstance(list(parameters.values())[0], dict):
            # Legacy format where each param is a dict with 'type', 'required', etc.
            required_params = [
                name
                for name, info in parameters.items()
                if isinstance(info, dict) and info.get("required", False)
            ]

            if required_params:
                example_params = []
                for param_name in required_params:
                    param_info = parameters[param_name]
                    param_type = param_info.get("type", "string")
                    if "string" in param_type.lower():
                        example_params.append(f'{param_name}="EXAMPLE"')
                    elif "integer" in param_type.lower():
                        example_params.append(f"{param_name}=100")
                    elif "boolean" in param_type.lower():
                        example_params.append(f"{param_name}=True")
                    else:
                        example_params.append(f"{param_name}=<value>")

                examples.append(f"{tool_name}({', '.join(example_params)})")

            # All parameters
            if len(parameters) > len(required_params):
                all_params = []
                for param_name, param_info in parameters.items():
                    if isinstance(param_info, dict):
                        param_type = param_info.get("type", "string")
                        if "string" in param_type.lower():
                            all_params.append(f'{param_name}="EXAMPLE"')
                        elif "integer" in param_type.lower():
                            all_params.append(f"{param_name}=100")
                        elif "boolean" in param_type.lower():
                            all_params.append(f"{param_name}=True")
                        else:
                            all_params.append(f"{param_name}=<value>")

                examples.append(f"{tool_name}({', '.join(all_params)})")

        else:
            # JSON Schema format - parameters are schema properties directly
            example_params = []
            for param_name, param_schema in parameters.items():
                if isinstance(param_schema, dict):
                    param_type = param_schema.get("type", "string")
                    if param_type == "string":
                        example_params.append(f'{param_name}="EXAMPLE"')
                    elif param_type == "integer":
                        example_params.append(f"{param_name}=100")
                    elif param_type == "boolean":
                        example_params.append(f"{param_name}=True")
                    else:
                        example_params.append(f"{param_name}=<value>")

            if example_params:
                examples.append(f"{tool_name}({', '.join(example_params)})")

        return examples if examples else [f"{tool_name}()"]

    def _generate_prompt_examples(self, prompt_name: str, parameters: dict[str, Any]) -> list[str]:
        """Generate usage examples for a prompt/workflow."""
        examples = []

        if not parameters:
            examples.append(f"{prompt_name}()")
        else:
            # Create example with realistic values based on prompt name
            example_params = []
            for param_name, param_info in parameters.items():
                if param_name == "symbol" or param_name == "symbols":
                    example_params.append(f'{param_name}="AAPL"')
                elif param_name == "scan_type":
                    example_params.append(f'{param_name}="momentum"')
                elif param_name == "timeframe":
                    example_params.append(f'{param_name}="1Min"')
                elif "str" in param_info["type"].lower():
                    example_params.append(f'{param_name}="example"')
                elif "int" in param_info["type"].lower():
                    example_params.append(f"{param_name}=5")
                elif "bool" in param_info["type"].lower():
                    example_params.append(f"{param_name}=True")
                else:
                    example_params.append(f"{param_name}=<value>")

            examples.append(f"{prompt_name}({', '.join(example_params)})")

        return examples

    def _find_related_tools(self, tool_name: str) -> list[str]:
        """Find related tools based on naming patterns and categories."""
        related = []
        category = self._categorize_tool(tool_name)

        for other_tool in self._tool_registry:
            if other_tool != tool_name and self._categorize_tool(other_tool) == category:
                related.append(other_tool)

        return related[:5]  # Limit to 5 related tools

    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tools based on naming patterns."""
        if "account" in tool_name.lower() or "position" in tool_name.lower():
            return "Account & Portfolio"
        elif "order" in tool_name.lower():
            return "Order Management"
        elif (
            "stock" in tool_name.lower()
            or "quote" in tool_name.lower()
            or "bar" in tool_name.lower()
        ):
            return "Market Data"
        elif "scan" in tool_name.lower():
            return "Scanners & Analysis"
        elif "stream" in tool_name.lower():
            return "Real-time Streaming"
        elif "option" in tool_name.lower():
            return "Options Trading"
        elif "market" in tool_name.lower() or "clock" in tool_name.lower():
            return "Market Info"
        elif "asset" in tool_name.lower() or "watchlist" in tool_name.lower():
            return "Assets & Organization"
        elif "cleanup" in tool_name.lower() or "clean" in tool_name.lower():
            return "System Maintenance"
        elif "help" in tool_name.lower() or "debug" in tool_name.lower():
            return "Help & Debugging"
        elif "monitor" in tool_name.lower() or "fastapi" in tool_name.lower():
            return "Monitoring Services"
        else:
            return "Other"

    def get_tool_help(self, tool_name: str) -> str:
        """Get formatted help for a specific tool."""
        # Refresh registries to get latest tools
        self._update_tool_registry()

        if tool_name not in self._tool_registry:
            available_tools = ", ".join(sorted(self._tool_registry.keys()))
            return f"""
❌ Tool '{tool_name}' not found.

Available tools: {available_tools}

Use get_all_tools_help() to see all available tools.
"""

        tool_info = self._tool_registry[tool_name]

        # Generate MCP-compliant help text
        annotations = tool_info.get("annotations", {})
        input_schema = tool_info.get("input_schema", {})

        help_text = f"""
📋 **{annotations.get("title", tool_info["name"])}** ({tool_info["category"]})
{"-" * (len(annotations.get("title", tool_info["name"])) + len(tool_info["category"]) + 7)}

**Description**: {tool_info["description"]}

**MCP Tool Schema**:
  • Name: `{tool_info["name"]}`
  • Type: Object with {len(input_schema.get("properties", {}))} parameters
  • Required: {input_schema.get("required", [])}

**Behavior Annotations**:
"""

        if annotations.get("readOnlyHint") is not None:
            help_text += f"  • Read-only: {'Yes' if annotations['readOnlyHint'] else 'No'}\n"
        if annotations.get("destructiveHint"):
            help_text += "  • Destructive: Yes ⚠️\n"
        if annotations.get("idempotentHint"):
            help_text += "  • Idempotent: Yes (safe to retry)\n"
        if annotations.get("openWorldHint") is not None:
            help_text += (
                f"  • External interactions: {'Yes' if annotations['openWorldHint'] else 'No'}\n"
            )

        help_text += "\n**Usage Examples**:\n"
        for example in tool_info["usage_examples"]:
            help_text += f"  • {example}\n"

        # Show JSON Schema parameters
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        if properties:
            help_text += "\n**Parameters (JSON Schema)**:\n"
            for param_name, param_schema in properties.items():
                required_marker = " (required)" if param_name in required else ""
                default_marker = (
                    f" (default: {param_schema.get('default')})"
                    if "default" in param_schema
                    else ""
                )
                help_text += f"  • **{param_name}** ({param_schema.get('type', 'string')}){required_marker}{default_marker}\n"
                help_text += f"    {param_schema.get('description', 'No description available')}\n"

        if tool_info["related_tools"]:
            help_text += f"\n**Related Tools**: {', '.join(tool_info['related_tools'])}\n"

        help_text += f"\n**Returns**: {tool_info['return_type']}\n"

        if tool_info["full_description"] != tool_info["description"]:
            help_text += f"\n**Details**:\n{tool_info['full_description']}\n"

        return help_text

    def get_prompt_help(self, prompt_name: str) -> str:
        """Get formatted help for a specific prompt/workflow."""
        # Refresh registries to get latest prompts
        self._update_prompt_registry()

        if prompt_name not in self._prompt_registry:
            available_prompts = ", ".join(sorted(self._prompt_registry.keys()))
            return f"""
❌ Prompt '{prompt_name}' not found.

Available prompts: {available_prompts}

Use get_all_prompts_help() to see all available prompts.
"""

        prompt_info = self._prompt_registry[prompt_name]

        help_text = f"""
🚀 **{prompt_info["name"]}** (Workflow)
{"-" * (len(prompt_info["name"]) + 12)}

**Description**: {prompt_info["description"]}

**Usage Examples**:
"""

        for example in prompt_info["usage_examples"]:
            help_text += f"  • {example}\n"

        if prompt_info["parameters"]:
            help_text += "\n**Parameters**:\n"
            for param_name, param_info in prompt_info["parameters"].items():
                required_marker = (
                    " (required)"
                    if param_info["required"]
                    else f" (default: {param_info['default']})"
                )
                help_text += f"  • **{param_name}** ({param_info['type']}){required_marker}\n"
                help_text += f"    {param_info['description']}\n"

        if prompt_info["full_description"] != prompt_info["description"]:
            help_text += f"\n**Details**:\n{prompt_info['full_description']}\n"

        return help_text

    def get_all_tools_help(self) -> str:
        """Get help for all tools organized by category."""
        # Refresh registries to get latest tools
        self._update_tool_registry()

        categories: dict[str, list[Any]] = {}

        for _tool_name, tool_info in self._tool_registry.items():
            category = tool_info["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_info)

        help_text = """
🔧 **ALL TOOLS REFERENCE**
========================

"""

        for category, tools in sorted(categories.items()):
            help_text += f"## {category} ({len(tools)} tools)\n"
            for tool in sorted(tools, key=lambda x: x["name"]):
                help_text += f"  • **{tool['name']}** - {tool['description']}\n"
            help_text += "\n"

        help_text += f"""
**Total Tools**: {len(self._tool_registry)}
**Total Prompts**: {len(self._prompt_registry)}
**Total Resources**: {len(self._resource_registry)}

**Usage**: Use get_tool_help("tool_name") for detailed information about any tool.
"""

        return help_text

    def get_all_prompts_help(self) -> str:
        """Get help for all prompts/workflows."""
        help_text = """
🚀 **ALL WORKFLOWS REFERENCE**
============================

"""

        for prompt_name, prompt_info in sorted(self._prompt_registry.items()):
            help_text += f"  • **{prompt_name}** - {prompt_info['description']}\n"

        help_text += f"""
**Total Workflows**: {len(self._prompt_registry)}

**Usage**: Use get_prompt_help("prompt_name") for detailed information about any workflow.
"""

        return help_text

    def search_tools(self, query: str) -> str:
        """Search tools by name or description."""
        # Refresh registries to get latest tools
        self._update_tool_registry()

        query = query.lower()
        matches = []

        for tool_name, tool_info in self._tool_registry.items():
            if (
                query in tool_name.lower()
                or query in tool_info["description"].lower()
                or query in tool_info["category"].lower()
            ):
                matches.append(tool_info)

        if not matches:
            return f"No tools found matching '{query}'. Use get_all_tools_help() to see all available tools."

        help_text = f"""
🔍 **SEARCH RESULTS FOR '{query}'**
{"-" * (len(query) + 25)}

Found {len(matches)} matching tools:

"""

        for tool in sorted(matches, key=lambda x: x["name"]):
            help_text += f"  • **{tool['name']}** ({tool['category']}) - {tool['description']}\n"

        help_text += '\n**Usage**: Use get_tool_help("tool_name") for detailed information.\n'

        return help_text

    def get_mcp_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Get MCP-compliant tool schema for tools/list response."""
        self._update_tool_registry()

        if tool_name not in self._tool_registry:
            return None

        tool_info = self._tool_registry[tool_name]

        # Build MCP-compliant tool definition
        mcp_tool = {
            "name": tool_info["name"],
            "description": tool_info["description"],
            "inputSchema": tool_info["input_schema"],
        }

        # Add annotations if present
        if tool_info.get("annotations"):
            mcp_tool["annotations"] = tool_info["annotations"]

        return mcp_tool

    def get_all_mcp_tool_schemas(self) -> list[dict[str, Any]]:
        """Get all tools in MCP-compliant format for tools/list response."""
        self._update_tool_registry()

        mcp_tools = []
        for tool_name in self._tool_registry:
            schema = self.get_mcp_tool_schema(tool_name)
            if schema:
                mcp_tools.append(schema)

        return mcp_tools

    def export_mcp_tools_list(self) -> dict[str, Any]:
        """Export complete MCP tools/list response format."""
        return {"tools": self.get_all_mcp_tool_schemas()}


# Global help system instance (will be initialized when server starts)
_help_system: HelpSystem | None = None


def initialize_help_system(mcp_server: FastMCP):
    """Initialize the global help system."""
    global _help_system
    _help_system = HelpSystem(mcp_server)


def get_help_system() -> HelpSystem:
    """Get the global help system instance."""
    if _help_system is None:
        raise RuntimeError("Help system not initialized. Call initialize_help_system() first.")
    return _help_system


# Resource functions for MCP server registration
async def get_tool_help_resource(tool_name: str) -> str:
    """Resource endpoint for tool help."""
    return get_help_system().get_tool_help(tool_name)


async def get_all_tools_help_resource() -> str:
    """Resource endpoint for all tools help."""
    return get_help_system().get_all_tools_help()


async def get_prompt_help_resource(prompt_name: str) -> str:
    """Resource endpoint for prompt help."""
    return get_help_system().get_prompt_help(prompt_name)


async def search_tools_resource(query: str) -> str:
    """Resource endpoint for tool search."""
    return get_help_system().search_tools(query)


async def get_all_prompts_help_resource() -> str:
    """Resource endpoint for all prompts help."""
    return get_help_system().get_all_prompts_help()


# ============================================================================
# HELP PARAMETER DECORATOR - CLI-style --help support
# ============================================================================


def with_help_support(tool_name: str):
    """
    Decorator to add --help parameter support to any tool.

    Usage:
        @with_help_support("tool_name")
        async def my_tool(param1: str, help: str = None) -> str:
            # Tool implementation
            pass
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Check if help parameter is provided
            help_param = kwargs.get("help")
            if help_param == "--help" or help_param == "help":
                return get_help_system().get_tool_help(tool_name)

            # Remove help parameter if present but not requesting help
            if "help" in kwargs and kwargs["help"] is None:
                kwargs.pop("help")

            # Call original function
            return await func(*args, **kwargs)

        # Preserve original function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__annotations__ = func.__annotations__

        return wrapper

    return decorator


def check_help_parameter(**kwargs) -> str | None:
    """
    Utility function to check for help parameter in tool calls.

    Returns help text if help is requested, None otherwise.

    Usage in tools:
        help_response = check_help_parameter(**locals())
        if help_response:
            return help_response
    """
    for key, value in kwargs.items():
        if key.lower() == "help" and (value == "--help" or value == "help"):
            # Extract tool name from call stack
            import inspect

            frame = inspect.currentframe()
            tool_name = frame.f_back.f_code.co_name if frame and frame.f_back else "unknown_tool"
            return get_help_system().get_tool_help(tool_name)
    return None
