def register(mcp):
    @mcp.tool()
    def locate_ignore_check_in_expand_modules(repo_root: str) -> str:
        """Locate the exact line in expand_modules.py where subfilepath is checked against ignore_list_paths_re.
        
        Args:
            repo_root: Path to the pylint repository root
            
        Returns:
            JSON with file path, line number, and surrounding context
        """
        import os
        import json
        
        target_file = os.path.join(repo_root, "pylint", "lint", "expand_modules.py")
        
        if not os.path.exists(target_file):
            return json.dumps({
                "status": "error",
                "message": f"File not found: {target_file}"
            })
        
        with open(target_file, 'r') as f:
            lines = f.readlines()
        
        # Look for the line checking subfilepath against ignore_list_paths_re
        target_line = None
        for i, line in enumerate(lines, 1):
            if "_is_in_ignore_list_re(subfilepath, ignore_list_paths_re)" in line:
                target_line = i
                break
        
        if target_line is None:
            return json.dumps({
                "status": "error",
                "message": "Could not find the target line checking subfilepath"
            })
        
        # Get context (5 lines before and after)
        start = max(0, target_line - 6)
        end = min(len(lines), target_line + 5)
        context = "".join(lines[start:end])
        
        return json.dumps({
            "status": "ok",
            "file": target_file,
            "line": target_line,
            "content": lines[target_line - 1].rstrip(),
            "context": context
        }, indent=2)
