def register(mcp):
    @mcp.tool()
    def write_sitecustomize():
        import os, sys
        repo_root = os.path.abspath(os.path.dirname(__file__))
        src_path = os.path.join(repo_root, "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        # Write the sitecustomize.py file
        with open(os.path.join(repo_root, "sitecustomize.py"), "w") as f:
            f.write("import os\nimport sys\n\nrepo_root = os.path.abspath(os.path.dirname(__file__))\nsrc_path = os.path.join(repo_root, 'src')\nif src_path not in sys.path:\n    sys.path.insert(0, src_path)\n")
        return "sitecustomize.py written"
