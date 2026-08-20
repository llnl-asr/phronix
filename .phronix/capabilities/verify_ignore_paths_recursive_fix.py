import subprocess
import tempfile
import os

def register(mcp):
    @mcp.tool()
    def verify_ignore_paths_recursive_fix(repo_root: str) -> str:
        """Reproduce the src/gen leaf-file --ignore-paths/--recursive=y case
        against the given pylint repo checkout and run the expand_modules /
        pylinter file-discovery test files. Returns a pass/fail summary."""
        results = []
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "src", "gen"))
            with open(os.path.join(tmp, "src", "main.py"), "w") as f:
                f.write("x = 1\n")
            with open(os.path.join(tmp, "src", "gen", "about.py"), "w") as f:
                f.write("y = 2\n")
            script = (
                "import sys; sys.path.insert(0, %r)\n"
                "from pylint.lint.pylinter import PyLinter\n"
                "linter = PyLinter()\n"
                "linter._parse_configuration_file(['--recursive=y', '--ignore-paths=^src/gen/.*$'])\n"
                "linter.config.recursive = True\n"
                "files = list(linter._discover_files([%r]))\n"
                "print('DISCOVERED:', files)\n"
                "assert not any('gen' in f for f in files), 'leaf file under ignored path was not filtered'\n"
            ) % (repo_root, os.path.join(tmp, "src"))
            proc = subprocess.run(["python3", "-c", script], capture_output=True, text=True)
            results.append("repro: " + ("PASS" if proc.returncode == 0 else "FAIL: " + proc.stderr))

        for testfile in ("tests/lint/unittest_expand_modules.py", "tests/test_self.py"):
            path = os.path.join(repo_root, testfile)
            if os.path.exists(path):
                proc = subprocess.run(
                    ["python3", "-m", "pytest", path, "-q"],
                    cwd=repo_root, capture_output=True, text=True,
                )
                results.append(f"{testfile}: " + ("PASS" if proc.returncode == 0 else "FAIL"))

        return "\n".join(results)
