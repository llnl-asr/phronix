"""Locate a function definition in the codebase.

This capability finds where a function is defined and returns its exact
location including file path and line numbers.
"""

import re
import subprocess
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def locate_function_in_file(
        function_name: str,
        search_path: str = "."
    ) -> str:
        """Find the exact location of a function definition.
        
        Args:
            function_name: The name of the function to locate (e.g., '_is_ignored_file')
            search_path: Root directory to search from (defaults to current directory)
            
        Returns:
            JSON string with location details or error message
        """
        import json
        
        try:
            # Use ripgrep to find function definitions
            # Pattern matches: "def function_name(" at start of line or after whitespace
            pattern = rf"^\s*def\s+{re.escape(function_name)}\s*\("
            
            result = subprocess.run(
                ["rg", "--json", "-e", pattern, search_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            matches = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get('type') == 'match':
                        matches.append({
                            'file': data['data']['path']['text'],
                            'line': data['data']['line_number'],
                            'text': data['data']['lines']['text'].strip()
                        })
                except json.JSONDecodeError:
                    continue
            
            if not matches:
                return json.dumps({
                    'status': 'not_found',
                    'function': function_name,
                    'message': f'Function {function_name} not found in {search_path}'
                })
            
            return json.dumps({
                'status': 'found',
                'function': function_name,
                'matches': matches,
                'count': len(matches)
            }, indent=2)
            
        except subprocess.TimeoutExpired:
            return json.dumps({'status': 'error', 'message': 'Search timeout'})
        except FileNotFoundError:
            return json.dumps({'status': 'error', 'message': 'ripgrep (rg) not found'})
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)})
