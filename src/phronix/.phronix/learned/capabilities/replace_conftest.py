def register(mcp):
    import os, urllib.request, hashlib, shutil
    @mcp.tool()
    def replace_conftest(root: str) -> str:
        """Replace tests/conftest.py with the upstream version.

        Args:
            root: Path to the repository root.
        Returns:
            Confirmation message.
        """
        url = "https://raw.githubusercontent.com/pallets/flask/2.3.0/tests/conftest.py"
        dest = os.path.join(root, "tests", "conftest.py")
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        return f"Replaced {dest}"