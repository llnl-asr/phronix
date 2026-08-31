def register(mcp):
    import subprocess
    
    @mcp.tool()
    def apply_pylint_path_normalization_fix(repo_path: str = ".") -> str:
        """Apply the path normalization fix to pylint/lint/expand_modules.py.
        
        Adds 'element = os.path.normpath(element)' at the beginning of the
        _is_ignored_file function to normalize paths before checking against
        ignore-paths regex patterns. This fixes the bug where Windows backslash
        paths don't match forward-slash regex patterns.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            Status message indicating success or failure
        """
        import os
        
        file_path = os.path.join(repo_path, "pylint", "lint", "expand_modules.py")
        
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if already applied
        if "element = os.path.normpath(element)" in content:
            return f"Fix already applied to {file_path}"
        
        # Find the _is_ignored_file function and add the normpath line
        lines = content.split('\n')
        modified_lines = []
        in_function = False
        fix_applied = False
        
        for i, line in enumerate(lines):
            modified_lines.append(line)
            
            # Detect the function start
            if 'def _is_ignored_file(' in line:
                in_function = True
            
            # Add the fix after the function signature and before basename line
            if in_function and not fix_applied and 'basename = os.path.basename(element)' in line:
                # Insert the normpath line before the basename line
                modified_lines.pop()  # Remove the basename line we just added
                modified_lines.append('    element = os.path.normpath(element)')
                modified_lines.append(line)  # Add the basename line back
                fix_applied = True
                in_function = False
        
        if not fix_applied:
            return f"ERROR: Could not find the insertion point in {file_path}"
        
        # Write the modified content
        with open(file_path, 'w') as f:
            f.write('\n'.join(modified_lines))
        
        return f"Successfully applied path normalization fix to {file_path}"
