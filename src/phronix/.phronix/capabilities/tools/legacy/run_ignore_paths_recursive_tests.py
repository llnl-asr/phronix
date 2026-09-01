import subprocess


def register(mcp):
    @mcp.tool()
    def run_ignore_paths_recursive_tests(repo_root: str) -> str:
        """Run tests/test_self.py -k ignore and
        tests/lint/unittest_expand_modules.py under pytest in repo_root,
        returning combined stdout/stderr, to check the ignore-paths
        --recursive=y fix for regressions.
        """
        cmds = [
            ["python", "-m", "pytest", "-q", "tests/test_self.py", "-k", "ignore"],
            ["python", "-m", "pytest", "-q", "tests/lint/unittest_expand_modules.py"],
        ]
        output = []
        for cmd in cmds:
            proc = subprocess.run(
                cmd, cwd=repo_root, capture_output=True, text=True, timeout=600
            )
            output.append(f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
        return "\n\n".join(output)
