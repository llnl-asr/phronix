"""
Normalize file paths before checking if they should be ignored in pylint.

This capability applies the fix for pylint issue #6964 / PR #7080 where
ignore-paths configuration was not working with --recursive=y because paths
on Windows use backslashes while patterns use forward slashes.
"""

def register(mcp):
    @mcp.tool()
    def normalize_path_before_ignore_check(file_path: str) -> str:
        """
        Apply the fix to normalize paths in _is_ignored_file function.
        
        Args:
            file_path: Path to pylint/lint/expand_modules.py
            
        Returns:
            Status message indicating success or failure
        """
        import os
        
        # Read the file
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Find the line to modify - look for the _is_ignored_file function
        # and add normpath call right after the function signature
        insert_index = None
        for i, line in enumerate(lines):
            if i >= 53 and ') -> bool:' in line and i < 60:
                # Check if this is the _is_ignored_file function
                if any('_is_ignored_file' in lines[j] for j in range(max(0, i-5), i)):
                    insert_index = i + 1
                    break
        
        if not insert_index:
            return "ERROR: Could not find insertion point in _is_ignored_file function"
        
        # Check if already applied
        if insert_index < len(lines) and 'os.path.normpath(element)' in lines[insert_index]:
            return "INFO: Fix already applied"
        
        # Insert the normpath line
        indent = '    '  # 4 spaces for function body
        lines.insert(insert_index, f'{indent}element = os.path.normpath(element)\\n')
        
        # Write back
        with open(file_path, 'w') as f:
            f.writelines(lines)
        
        return f"SUCCESS: Added os.path.normpath() at line {insert_index + 1}"
