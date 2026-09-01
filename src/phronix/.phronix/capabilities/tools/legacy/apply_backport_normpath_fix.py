"""Apply normpath fix to _is_ignored_file in pylint/lint/expand_modules.py.

This is the one-line fix from PR #7080 that normalizes paths before
checking them against ignore-patterns regex.
"""

import os
import re


def register(mcp):
    @mcp.tool()
    def apply_pylint_normpath_fix(file_path: str = "pylint/lint/expand_modules.py") -> str:
        """Apply os.path.normpath fix to _is_ignored_file function.
        
        Args:
            file_path: Path to expand_modules.py file
            
        Returns:
            Status message indicating success or failure
        """
        
        if not os.path.exists(file_path):
            return f"Error: {file_path} not found"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find _is_ignored_file function
        # The fix adds: element = os.path.normpath(element)
        # right before the ignore-paths regex check
        
        # Pattern to find the function and injection point
        # Looking for the function definition and the first line that checks patterns
        pattern = r'(def _is_ignored_file\([^)]+\)[^:]*:.*?)(for pattern in)'
        
        def add_normpath(match):
            func_start = match.group(1)
            for_line = match.group(2)
            # Add normpath call before the loop
            return f'{func_start}    element = os.path.normpath(element)\n    {for_line}'
        
        # Check if already applied
        if 'os.path.normpath(element)' in content:
            return "Fix already applied: os.path.normpath(element) found in file"
        
        new_content = re.sub(pattern, add_normpath, content, flags=re.DOTALL)
        
        if new_content == content:
            return "Error: Could not find injection point in _is_ignored_file function"
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        return "Successfully applied normpath fix to _is_ignored_file function"
