#!/usr/bin/env python3
"""Apply surgical normalization fix to pylint expand_modules."""

import os
import re


def register(mcp):
    @mcp.tool()
    def apply_surgical_normalization_fix(repo_root: str = ".") -> str:
        """Apply the surgical normalization fix to _is_ignored_file.
        
        Modifies pylint/lint/expand_modules.py line 59 to normalize element
        only when checking against ignore_list_paths_re, not for basename checks.
        
        Args:
            repo_root: Root directory of the pylint repository
            
        Returns:
            Status message indicating success or failure
        """
        import os
        
        file_path = os.path.join(repo_root, "pylint/lint/expand_modules.py")
        
        if not os.path.exists(file_path):
            return f"ERROR: File not found: {file_path}"
        
        with open(file_path, "r") as f:
            lines = f.readlines()
        
        # Find the line with the ignore_list_paths_re check
        modified = False
        for i, line in enumerate(lines):
            # Look for the pattern: _is_in_ignore_list_re(element, ignore_list_paths_re)
            if "_is_in_ignore_list_re(element, ignore_list_paths_re)" in line:
                # Replace with normalized version
                lines[i] = line.replace(
                    "_is_in_ignore_list_re(element, ignore_list_paths_re)",
                    "_is_in_ignore_list_re(os.path.normpath(element), ignore_list_paths_re)"
                )
                modified = True
                break
        
        if not modified:
            return "ERROR: Could not find the target line to modify"
        
        with open(file_path, "w") as f:
            f.writelines(lines)
        
        return f"SUCCESS: Modified {file_path} line {i+1}"
