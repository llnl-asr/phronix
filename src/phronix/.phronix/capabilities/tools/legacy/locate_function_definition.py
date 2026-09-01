import ast

def register(mcp):
    @mcp.tool()
    def locate_function_definition(file_path: str, name: str, context: int = 5) -> str:
        """Locate a function or class definition named *name* in *file_path*.

        Returns the source lines (with line numbers) from the definition's
        start through its end, plus *context* trailing lines, so a caller can
        see the full body without opening the file separately.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()
        lines = src.splitlines()
        tree = ast.parse(src, filename=file_path)
        target = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                target = node
                break
        if target is None:
            return f"NOT FOUND: {name} in {file_path}"
        start = target.lineno
        end = getattr(target, "end_lineno", start) + context
        end = min(end, len(lines))
        out = []
        for i in range(start, end + 1):
            if 1 <= i <= len(lines):
                out.append(f"{i}\t{lines[i-1]}")
        return "\n".join(out)
