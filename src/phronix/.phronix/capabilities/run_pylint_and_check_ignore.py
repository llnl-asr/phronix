def register(mcp):
    @mcp.tool()
    def run_pylint_and_check_ignore():
        """Run pylint recursively on src/ and check that src/gen files are ignored."""
        import subprocess, re, os
        # Ensure we are at project root
        cwd = os.getcwd()
        # Run pylint
        result = subprocess.run(['pylint', '--recursive=y', 'src/'], cwd=cwd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        # Determine if any src/gen paths appear in output
        ignored = not re.search(r'src[\\/]gen[\\/]', output)
        return {'passed': ignored, 'output': output}
