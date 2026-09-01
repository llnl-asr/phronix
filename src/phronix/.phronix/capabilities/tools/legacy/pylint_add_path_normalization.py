"""Add path normalization to fix ignore-paths in recursive mode.

This capability implements the fix from pylint PR #7080 which adds path normalization
before checking if a file should be ignored. Without normalization, paths like ./src/gen/
don't match regex patterns like ^src/gen/.*$ because of the leading ./ component.
"""

from pathlib import Path
import re

def register(mcp):
    @mcp.tool()
    def pylint_add_path_normalization(repo_root: str) -> str:
        """Add os.path.normpath() to _is_ignored_file() in pylint/lint/expand_modules.py.
        
        Args:
            repo_root: Path to the pylint repository root
            
        Returns:
            Status message indicating success or failure
        """
        expand_modules_path = Path(repo_root) / "pylint" / "lint" / "expand_modules.py"
        
        if not expand_modules_path.exists():
            return f"ERROR: File not found: {expand_modules_path}"
        
        # Read the current content
        content = expand_modules_path.read_text()
        
        # Check if the fix is already applied
        if "element = os.path.normpath(element)" in content:
            return "INFO: Path normalization already present in _is_ignored_file()"
        
        # Find the _is_ignored_file function and add normalization
        # We need to insert "    element = os.path.normpath(element)\n" after the function signature
        # and before "basename = os.path.basename(element)"
        
        pattern = r'(def _is_ignored_file\([^)]+\) -> bool:\n)(    basename = os\.path\.basename\(element\))'
        replacement = r'\1    element = os.path.normpath(element)\n\2'
        
        new_content, count = re.subn(pattern, replacement, content)
        
        if count == 0:
            return "ERROR: Could not find the expected code pattern to patch"
        
        if count > 1:
            return f"ERROR: Found {count} matches, expected exactly 1"
        
        # Write the modified content
        expand_modules_path.write_text(new_content)
        
        return f"SUCCESS: Added path normalization to {expand_modules_path}"
