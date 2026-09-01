import os

def register(mcp):
    @mcp.tool()
    def build_nested_py_fixture(base_dir: str) -> str:
        """Create base_dir/subdirectory/module.py, base_dir/subdirectory/other.py,
        and base_dir/subdirectory/subsubdirectory/module.py, with no __init__.py
        anywhere so PyLinter._discover_files takes its loose-file (else) branch.
        Returns the list of created file paths, one per line."""
        paths = [
            os.path.join(base_dir, "subdirectory", "module.py"),
            os.path.join(base_dir, "subdirectory", "other.py"),
            os.path.join(base_dir, "subdirectory", "subsubdirectory", "module.py"),
        ]
        created = []
        for p in paths:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write("# fixture module\n")
            created.append(p)
        return "\n".join(created)
