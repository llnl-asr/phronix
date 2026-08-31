def register(mcp):
    import os
    import re
    
    @mcp.tool()
    def apply_path_normalization_fix(file_path: str) -> str:
        """Apply the fix to normalize paths in _is_ignored_file function.
        
        Args:
            file_path: Path to the expand_modules.py file
            
        Returns:
            Status message indicating success or failure
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Find the _is_ignored_file function and add normpath call
            # Pattern: find the function definition and the line with basename = os.path.basename(element)
            pattern = r'(def _is_ignored_file\([^)]+\) -> bool:\n)(    basename = os\.path\.basename\(element\))'
            replacement = r'\1    element = os.path.normpath(element)\n\2'
            
            if re.search(pattern, content):
                new_content = re.sub(pattern, replacement, content)
                with open(file_path, 'w') as f:
                    f.write(new_content)
                return f"Successfully added os.path.normpath(element) to _is_ignored_file in {file_path}"
            else:
                return f"Could not find the expected pattern in {file_path}"
                
        except Exception as e:
            return f"Error applying fix: {str(e)}"
