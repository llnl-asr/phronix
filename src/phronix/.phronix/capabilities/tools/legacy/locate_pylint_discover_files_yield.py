"""Capability to locate the file yielding location in _discover_files."""

def register(mcp):
    import os
    
    @mcp.tool()
    def locate_pylint_discover_files_yield(repo_path: str) -> str:
        """Find the exact location in pylinter.py where individual files are yielded.
        
        Args:
            repo_path: Path to the pylint repository root
            
        Returns:
            JSON string with file path and line numbers
        """
        import json
        
        pylinter_path = os.path.join(repo_path, "pylint", "lint", "pylinter.py")
        
        if not os.path.exists(pylinter_path):
            return json.dumps({"error": f"File not found: {pylinter_path}"})
        
        with open(pylinter_path, 'r') as f:
            lines = f.readlines()
        
        # Find the _discover_files method and the yield from statement
        in_discover_files = False
        yield_from_line = None
        method_start = None
        
        for i, line in enumerate(lines, 1):
            if 'def _discover_files' in line:
                in_discover_files = True
                method_start = i
            elif in_discover_files and 'yield from (' in line:
                yield_from_line = i
                break
        
        if yield_from_line:
            # Get the context (a few lines around it)
            start = max(0, yield_from_line - 5)
            end = min(len(lines), yield_from_line + 5)
            context = ''.join(lines[start:end])
            
            return json.dumps({
                "file": pylinter_path,
                "method_start_line": method_start,
                "yield_from_line": yield_from_line,
                "context": context,
                "fix_location": f"Lines {yield_from_line}-{yield_from_line+3}"
            }, indent=2)
        
        return json.dumps({"error": "Could not find yield from statement in _discover_files"})
