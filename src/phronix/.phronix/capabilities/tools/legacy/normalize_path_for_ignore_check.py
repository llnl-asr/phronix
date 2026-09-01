"""Normalize paths before ignore-paths matching in pylint.

Paths like ./some/path, some/path, and some//path should be treated identically
when matching against ignore-paths regex patterns.
"""

import os
import sys
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def normalize_path_in_is_ignored_file(repo_root: str) -> dict:
        """Normalize element path in _is_ignored_file before checking against patterns.
        
        Args:
            repo_root: Path to the pylint repository root
            
        Returns:
            dict with status, file, and changes made
        """
        expand_modules_path = Path(repo_root) / "pylint" / "lint" / "expand_modules.py"
        
        if not expand_modules_path.exists():
            return {
                "status": "error",
                "message": f"File not found: {expand_modules_path}"
            }
        
        content = expand_modules_path.read_text()
        
        # The fix: normalize element before checking
        # Original function checks element directly against patterns
        # We need to normalize it first
        original_function = '''def _is_ignored_file(
    element: str,
    ignore_list: list[str],
    ignore_list_re: list[Pattern[str]],
    ignore_list_paths_re: list[Pattern[str]],
) -> bool:
    basename = os.path.basename(element)
    return (
        basename in ignore_list
        or _is_in_ignore_list_re(basename, ignore_list_re)
        or _is_in_ignore_list_re(element, ignore_list_paths_re)
    )'''
        
        fixed_function = '''def _is_ignored_file(
    element: str,
    ignore_list: list[str],
    ignore_list_re: list[Pattern[str]],
    ignore_list_paths_re: list[Pattern[str]],
) -> bool:
    element = os.path.normpath(element)
    basename = os.path.basename(element)
    return (
        basename in ignore_list
        or _is_in_ignore_list_re(basename, ignore_list_re)
        or _is_in_ignore_list_re(element, ignore_list_paths_re)
    )'''
        
        if original_function in content:
            new_content = content.replace(original_function, fixed_function)
            expand_modules_path.write_text(new_content)
            return {
                "status": "ok",
                "file": str(expand_modules_path),
                "change": "Added os.path.normpath(element) at start of _is_ignored_file"
            }
        else:
            return {
                "status": "error",
                "message": "Could not find expected function signature to patch",
                "hint": "Function may have already been modified or signature changed"
            }
