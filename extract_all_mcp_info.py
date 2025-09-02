#!/usr/bin/env python
"""Extract complete MCP tools, resources, and prompts information"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alpaca_mcp_server.server import create_server
from alpaca_mcp_server.server_components.tool_registrations import register_all_tools
from alpaca_mcp_server.server_components.resource_registrations import register_all_resources
from alpaca_mcp_server.server_components.prompt_registrations import register_all_prompts

def extract_all_info():
    """Extract complete information about all tools, resources, and prompts"""
    
    # Create server instance
    server = create_server()
    
    # Extract Tools
    tools_info = []
    for tool_name, tool in server._tools.items():
        tool_data = {
            'name': tool_name,
            'description': tool.description or 'No description available',
            'parameters': {}
        }
        
        # Extract parameter information
        if hasattr(tool, 'input_schema') and tool.input_schema:
            schema = tool.input_schema
            if 'properties' in schema:
                for param_name, param_info in schema['properties'].items():
                    tool_data['parameters'][param_name] = {
                        'type': param_info.get('type', 'unknown'),
                        'description': param_info.get('description', ''),
                        'default': param_info.get('default', 'No default'),
                        'required': param_name in schema.get('required', [])
                    }
        
        tools_info.append(tool_data)
    
    # Extract Resources
    resources_info = []
    for resource_name, resource in server._resources.items():
        resource_data = {
            'name': resource_name,
            'uri': resource.uri if hasattr(resource, 'uri') else resource_name,
            'description': resource.description if hasattr(resource, 'description') else 'No description',
            'mime_type': getattr(resource, 'mime_type', 'application/json')
        }
        resources_info.append(resource_data)
    
    # Extract Prompts
    prompts_info = []
    for prompt_name, prompt in server._prompts.items():
        prompt_data = {
            'name': prompt_name,
            'description': prompt.description if hasattr(prompt, 'description') else 'No description',
            'arguments': []
        }
        
        if hasattr(prompt, 'arguments'):
            for arg in prompt.arguments:
                prompt_data['arguments'].append({
                    'name': arg.name,
                    'description': getattr(arg, 'description', ''),
                    'required': getattr(arg, 'required', False)
                })
        
        prompts_info.append(prompt_data)
    
    # Sort everything alphabetically
    tools_info.sort(key=lambda x: x['name'])
    resources_info.sort(key=lambda x: x['name'])
    prompts_info.sort(key=lambda x: x['name'])
    
    return {
        'tools': tools_info,
        'resources': resources_info,
        'prompts': prompts_info,
        'summary': {
            'total_tools': len(tools_info),
            'total_resources': len(resources_info),
            'total_prompts': len(prompts_info)
        }
    }

if __name__ == "__main__":
    info = extract_all_info()
    
    # Save to JSON file
    with open('mcp_complete_reference.json', 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"✅ Extracted {info['summary']['total_tools']} tools")
    print(f"✅ Extracted {info['summary']['total_resources']} resources")
    print(f"✅ Extracted {info['summary']['total_prompts']} prompts")
    print(f"📁 Saved to mcp_complete_reference.json")
    
    # Also print for immediate use
    print("\n" + "="*60)
    print("COMPLETE MCP REFERENCE")
    print("="*60)
    
    print(f"\n📦 TOOLS ({info['summary']['total_tools']} total):")
    for tool in info['tools']:
        print(f"\n• {tool['name']}")
        print(f"  Description: {tool['description'][:200]}...")
        if tool['parameters']:
            print(f"  Parameters:")
            for param, details in tool['parameters'].items():
                req = "required" if details['required'] else "optional"
                default = f", default={details['default']}" if details['default'] != 'No default' else ""
                print(f"    - {param} ({details['type']}, {req}{default})")
    
    print(f"\n📚 RESOURCES ({info['summary']['total_resources']} total):")
    for resource in info['resources']:
        print(f"\n• {resource['name']}")
        print(f"  URI: {resource['uri']}")
        print(f"  Description: {resource['description']}")
    
    print(f"\n🚀 PROMPTS ({info['summary']['total_prompts']} total):")
    for prompt in info['prompts']:
        print(f"\n• {prompt['name']}")
        print(f"  Description: {prompt['description']}")
        if prompt['arguments']:
            print(f"  Arguments:")
            for arg in prompt['arguments']:
                req = "required" if arg['required'] else "optional"
                print(f"    - {arg['name']} ({req}): {arg['description']}")