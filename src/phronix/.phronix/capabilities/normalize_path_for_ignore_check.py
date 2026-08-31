"""Apply path normalization before ignore-paths regex matching in pylint.

This capability implements the fix for issue #6964/#7080 where --recursive=y
was ignoring the ignore-paths configuration due to unnormalized paths not
matching the regex patterns.
"""

import os
import subprocess
import sys
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def normalize_path_for_ignore_check(repo_path: str) -> str:
        """Normalize paths before checking against ignore-paths regex in _is_ignored_file.
        
        Args:
            repo_path: Path to the pylint repository
            
        Returns:
            Status message indicating success or failure
        """
        expand_modules_path = Path(repo_path) / "pylint" / "lint" / "expand_modules.py"
        
        if not expand_modules_path.exists():
            return f"Error: {expand_modules_path} not found"
        
        # Read the current content
        content = expand_modules_path.read_text()
        
        # Find the _is_ignored_file function and modify it
        # Current line 59: or _is_in_ignore_list_re(element, ignore_list_paths_re)
        # Should become: or _is_in_ignore_list_re(os.path.normpath(element), ignore_list_paths_re)
        
        old_line = "or _is_in_ignore_list_re(element, ignore_list_paths_re)"
        new_line = "or _is_in_ignore_list_re(os.path.normpath(element), ignore_list_paths_re)"
        
        if old_line in content:
            new_content = content.replace(old_line, new_line)
            expand_modules_path.write_text(new_content)
            return f"Successfully normalized path in _is_ignored_file at {expand_modules_path}"
        elif new_line in content:
            return f"Path normalization already applied in {expand_modules_path}"
        else:
            return f"Error: Could not find expected line in {expand_modules_path}. Manual fix required."
