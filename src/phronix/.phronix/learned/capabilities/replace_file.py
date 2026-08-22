def register(mcp):
    @mcp.tool()
    def replace_file(url: str, dest: str) -> str:
        """Fetch content from `url` and write it to `dest`. Overwrites existing file.
        Returns a message indicating success.
        """
        import urllib.request
        import os
        data = urllib.request.urlopen(url).read()
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(data)
        return f"Replaced {dest} with content from {url}"
