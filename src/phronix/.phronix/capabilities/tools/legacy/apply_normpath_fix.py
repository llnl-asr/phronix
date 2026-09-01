"""Apply the normpath fix to pylint's _is_ignored_file function.

Adds element = os.path.normpath(element) at the start of _is_ignored_file
to normalize paths before checking against ignore patterns.
"""

import os
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def apply_normpath_fix(file_path: str) -> str:
        """Apply os.path.normpath fix to _is_ignored_file in expand_modules.py.
        
        Adds 'element = os.path.normpath(element)' at the beginning of the
        _is_ignored_file function to normalize paths before checking ignore patterns.
        
        Args:
            file_path: Path to pylint/lint/expand_modules.py
            
        Returns:
            Status message about the fix applied
        """
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"
            
        content = path.read_text()
        
        # Check if already fixed
        if "element = os.path.normpath(element)" in content:
            return "Fix already applied - os.path.normpath call already exists"
        
        # Find the _is_ignored_file function and add normpath call
        lines = content.split('\n')
        fixed_lines = []
        in_function = False
        fix_applied = False
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            
            # Look for the _is_ignored_file function definition
            if "def _is_ignored_file(" in line:
                in_function = True
                continue
                
            # If we're in the function and hit the first real line after params
            if in_function and not fix_applied:
                # Look for "basename = os.path.basename(element)"
                if "basename = os.path.basename(element)" in line:
                    # Insert normpath line before this line
                    indent = len(line) - len(line.lstrip())
                    normpath_line = " " * indent + "element = os.path.normpath(element)"
                    # Remove the line we just added, insert normpath, then add it back
                    fixed_lines.pop()
                    fixed_lines.append(normpath_line)
                    fixed_lines.append(line)
                    fix_applied = True
                    in_function = False
        
        if not fix_applied:
            return "Error: Could not find the location to insert the fix"
        
        # Write back
        path.write_text('\n'.join(fixed_lines))
        
        return f"Successfully applied fix to {file_path}: added os.path.normpath(element) in _is_ignored_file"
