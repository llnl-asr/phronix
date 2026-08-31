def register(mcp):
    @mcp.tool()
    def run_regression_tests():
        """Run the project's test suite using pytest and return pass/fail."""
        import subprocess, os
        cwd = os.getcwd()
        result = subprocess.run(['pytest', '-q'], cwd=cwd, capture_output=True, text=True)
        passed = result.returncode == 0
        return {'passed': passed, 'output': result.stdout + result.stderr}
