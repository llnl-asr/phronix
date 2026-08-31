"""Add path normalization for pylint ignore-paths fix."""

import re
from pathlib import Path


def register(mcp):
    @mcp.tool()
    def pylint_normalize_ignore_path(repo_path: str) -> str:
        """Add os.path.normpath(element) to _is_ignored_file function.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            Status message indicating success or failure
        """
        expand_modules_path = Path(repo_path) / "pylint" / "lint" / "expand_modules.py"
        
        if not expand_modules_path.exists():
            return f"Error: File not found at {expand_modules_path}"
        
        content = expand_modules_path.read_text()
        
        # Check if already patched
        if "element = os.path.normpath(element)" in content:
            return "Already patched: normpath call already exists"
        
        # Find the _is_ignored_file function and add normalization
        # The pattern looks for the function definition and the line after it
        pattern = r"(def _is_ignored_file\([^)]+\) -> bool:\n)"
        
        # Check if pattern matches
        if not re.search(pattern, content):
            return "Error: Could not find _is_ignored_file function signature"
        
        # Add the normalization line after the function signature
        replacement = r"\1    element = os.path.normpath(element)\n"
        new_content = re.sub(pattern, replacement, content, count=1)
        
        if new_content == content:
            return "Error: Pattern matched but no changes made"
        
        # Write the modified content
        expand_modules_path.write_text(new_content)
        
        return f"Successfully added path normalization to {expand_modules_path}"
