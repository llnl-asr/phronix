"""Capability to fix pylint ignore-paths handling in recursive mode.

Normalizes paths to forward slashes before matching against ignore-paths patterns.
"""

import os
import re


def register(mcp):
    @mcp.tool()
    def apply_ignore_paths_fix(repo_path: str) -> str:
        """Apply the path normalization fix to _is_ignored_file function.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            Status message indicating success or failure
        """
        import os.path as path
        
        file_path = path.join(repo_path, "pylint", "lint", "expand_modules.py")
        
        if not path.exists(file_path):
            return f"Error: File not found: {file_path}"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the line that needs to be changed
        # Original: or _is_in_ignore_list_re(element, ignore_list_paths_re)
        # New: or _is_in_ignore_list_re(element.replace(os.sep, "/"), ignore_list_paths_re)
        
        original_pattern = r'(\s+)or _is_in_ignore_list_re\(element, ignore_list_paths_re\)'
        replacement = r'\1or _is_in_ignore_list_re(element.replace(os.sep, "/"), ignore_list_paths_re)'
        
        new_content, count = re.subn(original_pattern, replacement, content)
        
        if count == 0:
            return "Error: Could not find the pattern to replace. File may have already been modified or structure changed."
        
        if count > 1:
            return f"Warning: Found {count} matches, expected 1. Review changes carefully."
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        return f"Success: Applied fix to {file_path}. Modified {count} occurrence(s)."
