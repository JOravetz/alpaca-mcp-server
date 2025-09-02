#!/usr/bin/env python3
"""
mcp_capability_scanner.py
Comprehensive scanner for MCP server capabilities - tools, resources, and prompts
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
import yaml
import re
from datetime import datetime

class MCPServerScanner:
    """
    Scans and analyzes MCP server to extract all capabilities
    for expert observation and intelligent hook generation
    """
    
    def __init__(self, server_path: str = None):
        self.server_path = server_path or self.find_mcp_server()
        self.capabilities = {
            'tools': [],
            'resources': [],
            'prompts': [],
            'metadata': {},
            'patterns': [],
            'integration_points': []
        }
        
    def find_mcp_server(self) -> Path:
        """Locate MCP server in current project"""
        possible_paths = [
            Path.cwd() / 'mcp.json',
            Path.cwd() / 'server' / 'mcp.json',
            Path.cwd() / 'src' / 'mcp.json',
            Path.home() / '.config' / 'mcp' / 'servers.json'
        ]
        
        for path in possible_paths:
            if path.exists():
                return path.parent
                
        # Check for any MCP config files
        mcp_files = list(Path.cwd().rglob('*mcp*.json'))
        if mcp_files:
            return mcp_files[0].parent
            
        return Path.cwd()
    
    def scan_tools(self) -> List[Dict]:
        """Extract all available tools from MCP server"""
        tools = []
        
        # Look for tool definitions in various formats
        tool_files = [
            self.server_path / 'tools.json',
            self.server_path / 'src' / 'tools.py',
            self.server_path / 'tools' / '*.json',
            self.server_path / 'schema' / 'tools.json'
        ]
        
        # Parse Python tool definitions
        py_files = list(self.server_path.rglob('*.py'))
        for py_file in py_files:
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Look for @tool decorators or tool definitions
                tool_pattern = r'@tool.*?def\s+(\w+)\([^)]*\).*?"""(.*?)"""'
                matches = re.findall(tool_pattern, content, re.DOTALL)
                
                for name, docstring in matches:
                    tools.append({
                        'name': name,
                        'description': docstring.strip(),
                        'file': str(py_file),
                        'type': 'function',
                        'parameters': self.extract_parameters(content, name)
                    })
                
                # Look for MCP tool definitions
                mcp_pattern = r'tools\s*=\s*\[(.*?)\]'
                mcp_matches = re.findall(mcp_pattern, content, re.DOTALL)
                if mcp_matches:
                    tools.extend(self.parse_mcp_tools(mcp_matches[0]))
        
        # Parse JSON tool definitions
        json_files = list(self.server_path.rglob('*tools*.json'))
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        tools.extend(data)
                    elif 'tools' in data:
                        tools.extend(data['tools'])
            except:
                pass
        
        self.capabilities['tools'] = tools
        return tools
    
    def scan_resources(self) -> List[Dict]:
        """Extract all available resources from MCP server"""
        resources = []
        
        # Look for resource definitions
        resource_patterns = [
            r'@resource.*?def\s+(\w+)',
            r'resources\s*=\s*\[(.*?)\]',
            r'ResourceProvider.*?def\s+(\w+)',
            r'get_resource.*?def\s+(\w+)'
        ]
        
        py_files = list(self.server_path.rglob('*.py'))
        for py_file in py_files:
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Check for resource definitions
                if 'resource' in content.lower():
                    # Extract resource methods
                    resource_method_pattern = r'def\s+(get_|fetch_|read_|list_)(\w+)\([^)]*\).*?"""(.*?)"""'
                    matches = re.findall(resource_method_pattern, content, re.DOTALL)
                    
                    for prefix, name, docstring in matches:
                        resources.append({
                            'name': f"{prefix}{name}",
                            'type': 'data_resource',
                            'description': docstring.strip(),
                            'file': str(py_file),
                            'access_pattern': prefix
                        })
        
        # Look for static resources
        static_resources = [
            'data/*.json',
            'config/*.yaml',
            'templates/*',
            'schemas/*.json'
        ]
        
        for pattern in static_resources:
            files = list(self.server_path.glob(pattern))
            for file in files:
                resources.append({
                    'name': file.stem,
                    'type': 'static_file',
                    'path': str(file),
                    'format': file.suffix[1:]
                })
        
        self.capabilities['resources'] = resources
        return resources
    
    def scan_prompts(self) -> List[Dict]:
        """Extract all available prompts from MCP server"""
        prompts = []
        
        # Look for prompt definitions
        prompt_files = [
            self.server_path / 'prompts.json',
            self.server_path / 'prompts' / '*.json',
            self.server_path / 'prompts' / '*.yaml',
            self.server_path / 'templates' / '*.md'
        ]
        
        # Search for prompt patterns in code
        py_files = list(self.server_path.rglob('*.py'))
        for py_file in py_files:
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Look for prompt definitions
                prompt_patterns = [
                    r'PROMPT\s*=\s*["\']+(.*?)["\']',
                    r'prompt\s*=\s*f?["\']+(.*?)["\']',
                    r'@prompt.*?def\s+(\w+)',
                    r'prompts\s*=\s*{(.*?)}'
                ]
                
                for pattern in prompt_patterns:
                    matches = re.findall(pattern, content, re.DOTALL)
                    for match in matches:
                        if isinstance(match, str) and len(match) > 20:
                            prompts.append({
                                'content': match[:200] + '...' if len(match) > 200 else match,
                                'file': str(py_file),
                                'type': 'embedded'
                            })
        
        # Look for markdown templates
        md_files = list(self.server_path.rglob('*.md'))
        for md_file in md_files:
            if 'prompt' in md_file.stem.lower() or 'template' in md_file.stem.lower():
                with open(md_file, 'r') as f:
                    content = f.read()
                    prompts.append({
                        'name': md_file.stem,
                        'content': content[:500] + '...' if len(content) > 500 else content,
                        'file': str(md_file),
                        'type': 'template'
                    })
        
        self.capabilities['prompts'] = prompts
        return prompts
    
    def analyze_patterns(self) -> List[Dict]:
        """Analyze usage patterns and workflows in the MCP server"""
        patterns = []
        
        # Look for workflow patterns
        py_files = list(self.server_path.rglob('*.py'))
        for py_file in py_files:
            with open(py_file, 'r') as f:
                content = f.read()
                
                # Find function call sequences
                if 'def ' in content:
                    functions = re.findall(r'def\s+(\w+)\([^)]*\):', content)
                    
                    # Look for functions that call other functions
                    for func in functions:
                        func_body = self.extract_function_body(content, func)
                        called_funcs = re.findall(r'(?:self\.)?([\w]+)\(', func_body)
                        
                        if len(called_funcs) > 2:
                            patterns.append({
                                'workflow': func,
                                'sequence': called_funcs,
                                'file': str(py_file),
                                'type': 'function_chain'
                            })
        
        self.capabilities['patterns'] = patterns
        return patterns
    
    def extract_parameters(self, content: str, function_name: str) -> Dict:
        """Extract function parameters and their types"""
        pattern = f'def\s+{function_name}\([^)]*\):'
        match = re.search(pattern, content)
        
        if match:
            # Extract parameter section
            param_pattern = f'def\s+{function_name}\(([^)]*)\)'
            param_match = re.search(param_pattern, content)
            
            if param_match:
                params_str = param_match.group(1)
                params = []
                
                # Parse parameters
                for param in params_str.split(','):
                    param = param.strip()
                    if param and param != 'self':
                        # Check for type hints
                        if ':' in param:
                            name, type_hint = param.split(':', 1)
                            params.append({
                                'name': name.strip(),
                                'type': type_hint.strip().replace('=', '').split()[0]
                            })
                        else:
                            params.append({'name': param.split('=')[0].strip()})
                
                return params
        
        return []
    
    def extract_function_body(self, content: str, function_name: str) -> str:
        """Extract the body of a function"""
        pattern = f'def\s+{function_name}\([^)]*\):.*?(?=\n\S|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(0) if match else ""
    
    def parse_mcp_tools(self, tools_str: str) -> List[Dict]:
        """Parse MCP tool definitions from string"""
        tools = []
        
        # Parse tool definitions
        tool_pattern = r'Tool\((.*?)\)'
        matches = re.findall(tool_pattern, tools_str, re.DOTALL)
        
        for match in matches:
            # Extract tool properties
            name_match = re.search(r'name=["\'](.*?)["\']', match)
            desc_match = re.search(r'description=["\'](.*?)["\']', match)
            
            if name_match:
                tools.append({
                    'name': name_match.group(1),
                    'description': desc_match.group(1) if desc_match else '',
                    'type': 'mcp_tool'
                })
        
        return tools
    
    def generate_capability_report(self) -> str:
        """Generate comprehensive capability report"""
        report = f"""
# MCP Server Capability Analysis
Generated: {datetime.now().isoformat()}
Server Path: {self.server_path}

## 🛠️ Tools ({len(self.capabilities['tools'])} found)
"""
        
        for tool in self.capabilities['tools']:
            params = tool.get('parameters', [])
            param_str = ', '.join([p.get('name', '') for p in params]) if params else 'none'
            report += f"\n### {tool['name']}\n"
            report += f"- **Type**: {tool.get('type', 'unknown')}\n"
            report += f"- **Description**: {tool.get('description', 'No description')}\n"
            report += f"- **Parameters**: ({param_str})\n"
            report += f"- **Location**: {tool.get('file', 'unknown')}\n"
        
        report += f"\n## 📦 Resources ({len(self.capabilities['resources'])} found)\n"
        
        for resource in self.capabilities['resources']:
            report += f"\n### {resource['name']}\n"
            report += f"- **Type**: {resource['type']}\n"
            report += f"- **Access**: {resource.get('access_pattern', 'direct')}\n"
            report += f"- **Location**: {resource.get('path', resource.get('file', 'unknown'))}\n"
        
        report += f"\n## 💬 Prompts ({len(self.capabilities['prompts'])} found)\n"
        
        for prompt in self.capabilities['prompts']:
            report += f"\n### {prompt.get('name', 'Embedded Prompt')}\n"
            report += f"- **Type**: {prompt['type']}\n"
            report += f"- **Preview**: {prompt['content'][:100]}...\n"
            report += f"- **Location**: {prompt['file']}\n"
        
        report += f"\n## 🔄 Workflow Patterns ({len(self.capabilities['patterns'])} found)\n"
        
        for pattern in self.capabilities['patterns']:
            report += f"\n### {pattern['workflow']}\n"
            report += f"- **Sequence**: {' → '.join(pattern['sequence'][:5])}\n"
            report += f"- **Location**: {pattern['file']}\n"
        
        return report
    
    def generate_hook_suggestions(self) -> List[Dict]:
        """Generate intelligent hook suggestions based on capabilities"""
        suggestions = []
        
        # Suggest hooks for common tool combinations
        tools = self.capabilities['tools']
        if len(tools) > 2:
            # Find tools that might work together
            analysis_tools = [t for t in tools if 'analyze' in t['name'].lower()]
            action_tools = [t for t in tools if any(x in t['name'].lower() for x in ['create', 'update', 'place', 'execute'])]
            
            if analysis_tools and action_tools:
                suggestions.append({
                    'name': 'auto_analysis_action',
                    'description': f"Automatically {action_tools[0]['name']} after {analysis_tools[0]['name']}",
                    'trigger': analysis_tools[0]['name'],
                    'action': action_tools[0]['name'],
                    'estimated_savings': '30-60 seconds'
                })
        
        # Suggest hooks for workflow patterns
        for pattern in self.capabilities['patterns']:
            if len(pattern['sequence']) > 3:
                suggestions.append({
                    'name': f"auto_{pattern['workflow']}",
                    'description': f"Automate the {pattern['workflow']} workflow",
                    'sequence': pattern['sequence'],
                    'estimated_savings': f"{len(pattern['sequence']) * 10} seconds"
                })
        
        return suggestions
    
    def export_to_claude_format(self) -> Dict:
        """Export capabilities in format ready for Claude to analyze"""
        return {
            'server_info': {
                'path': str(self.server_path),
                'scan_time': datetime.now().isoformat()
            },
            'capabilities': self.capabilities,
            'hook_suggestions': self.generate_hook_suggestions(),
            'integration_ready': True
        }
    
    def save_analysis(self, output_path: str = None):
        """Save the analysis results"""
        output_path = output_path or '.claude/mcp_analysis.json'
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.export_to_claude_format(), f, indent=2)
        
        # Also save human-readable report
        report_path = Path(output_path).with_suffix('.md')
        with open(report_path, 'w') as f:
            f.write(self.generate_capability_report())
        
        print(f"✅ Analysis saved to {output_path}")
        print(f"📄 Report saved to {report_path}")
        
        return output_path


class MCPHookGenerator:
    """
    Generates intelligent hooks based on MCP server capabilities
    """
    
    def __init__(self, capabilities: Dict):
        self.capabilities = capabilities
        
    def generate_tool_chain_hook(self, tools: List[str]) -> str:
        """Generate a hook that chains multiple tools together"""
        
        hook_code = f"""#!/usr/bin/env python3
import json
import sys
import subprocess

# Tool chain: {' → '.join(tools)}

def execute_chain():
    results = []
    
"""
        
        for i, tool in enumerate(tools):
            hook_code += f"""    # Step {i+1}: {tool}
    result_{i} = subprocess.run(
        ['mcp', 'call', '{tool}'],
        capture_output=True,
        text=True
    )
    results.append(result_{i}.stdout)
    
"""
        
        hook_code += """    return results

if __name__ == "__main__":
    try:
        results = execute_chain()
        print(f"✅ Completed {len(results)} steps successfully")
        for i, result in enumerate(results):
            print(f"Step {i+1}: {result[:100]}...")
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
"""
        
        return hook_code
    
    def generate_resource_monitor_hook(self, resource: str) -> str:
        """Generate a hook that monitors a resource for changes"""
        
        return f"""#!/usr/bin/env python3
import json
import time
import subprocess

# Monitor resource: {resource}

def monitor():
    last_value = None
    
    while True:
        result = subprocess.run(
            ['mcp', 'get', '{resource}'],
            capture_output=True,
            text=True
        )
        
        current_value = json.loads(result.stdout)
        
        if last_value and current_value != last_value:
            print(f"🔄 Resource changed: {resource}")
            print(f"   Old: {last_value}")
            print(f"   New: {current_value}")
            
            # Trigger action on change
            subprocess.run(['mcp', 'call', 'handle_{resource}_change'])
        
        last_value = current_value
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    monitor()
"""


def main():
    """Run the MCP server scanner"""
    
    print("🔍 Scanning MCP Server Capabilities...")
    print("-" * 60)
    
    scanner = MCPServerScanner()
    
    # Scan all capabilities
    print("\n📊 Scanning tools...")
    tools = scanner.scan_tools()
    print(f"   Found {len(tools)} tools")
    
    print("\n📦 Scanning resources...")
    resources = scanner.scan_resources()
    print(f"   Found {len(resources)} resources")
    
    print("\n💬 Scanning prompts...")
    prompts = scanner.scan_prompts()
    print(f"   Found {len(prompts)} prompts")
    
    print("\n🔄 Analyzing patterns...")
    patterns = scanner.analyze_patterns()
    print(f"   Found {len(patterns)} workflow patterns")
    
    # Generate report
    report = scanner.generate_capability_report()
    print("\n" + "=" * 60)
    print(report)
    
    # Generate hook suggestions
    suggestions = scanner.generate_hook_suggestions()
    if suggestions:
        print("\n🪝 Suggested Hooks:")
        for suggestion in suggestions:
            print(f"\n   • {suggestion['name']}")
            print(f"     {suggestion['description']}")
            print(f"     Saves: {suggestion['estimated_savings']}")
    
    # Save analysis
    output_path = scanner.save_analysis()
    
    # Export for Claude
    claude_data = scanner.export_to_claude_format()
    
    print("\n✨ Analysis Complete!")
    print(f"\nUse this data with the intelligent hook generator to create")
    print(f"automation specific to your MCP server's capabilities.")
    
    return claude_data


if __name__ == "__main__":
    capabilities = main()