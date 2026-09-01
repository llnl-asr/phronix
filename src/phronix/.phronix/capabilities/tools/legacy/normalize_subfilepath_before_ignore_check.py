def register(mcp):
    @mcp.tool()
    def normalize_subfilepath_before_ignore_check(repo_root: str) -> str:
        """Apply os.path.normpath() to subfilepath before checking against ignore_list_paths_re.
        
        Modifies line 145 in pylint/lint/expand_modules.py to normalize the path before
        pattern matching. This fixes the bug where --recursive=y ignores the ignore-paths
        configuration.
        
        Args:
            repo_root: Path to the pylint repository root
            
        Returns:
            JSON with status and details of the change
        """
        import os
        import json
        import re
        
        target_file = os.path.join(repo_root, "pylint", "lint", "expand_modules.py")
        
        if not os.path.exists(target_file):
            return json.dumps({
                "status": "error",
                "message": f"File not found: {target_file}"
            })
        
        with open(target_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Find the line with the pattern
        old_pattern = r'_is_in_ignore_list_re\(subfilepath, ignore_list_paths_re\)'
        new_text = '_is_in_ignore_list_re(os.path.normpath(subfilepath), ignore_list_paths_re)'
        
        # Check if already applied
        if new_text in content:
            return json.dumps({
                "status": "already_applied",
                "message": "The fix has already been applied",
                "file": target_file
            })
        
        # Apply the fix
        modified = False
        for i, line in enumerate(lines):
            if re.search(old_pattern, line):
                lines[i] = re.sub(old_pattern, new_text, line)
                modified = True
                line_number = i + 1
                break
        
        if not modified:
            return json.dumps({
                "status": "error",
                "message": "Could not find the target pattern to modify"
            })
        
        # Write back
        new_content = '\n'.join(lines)
        with open(target_file, 'w') as f:
            f.write(new_content)
        
        return json.dumps({
            "status": "ok",
            "message": "Successfully applied normalization fix",
            "file": target_file,
            "line": line_number,
            "change": f"Added os.path.normpath() wrapper around subfilepath"
        }, indent=2)
