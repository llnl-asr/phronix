import os
import subprocess
import sys
import tempfile


def register(mcp):
    @mcp.tool()
    def probe_run_ignore_paths_scenarios(repo_root: str, ignore_pattern: str = r"^dir/gen/.*$") -> str:
        """Reproduce / verify pylint's --recursive --ignore-paths file-discovery
        behavior across several invocation forms (bare relative dir, '.',
        trailing slash).

        Creates a temp tree:
            dir/normal.py
            dir/gen/ignored.py
        with *ignore_pattern* passed as --ignore-paths, then invokes pylint's
        expand_modules for each invocation form and reports whether
        dir/gen/ignored.py leaked into the discovered file list.

        Returns one "form: PASS/FAIL (files=[...])" line per scenario.
        """
        results = []
        with tempfile.TemporaryDirectory() as tmp:
            dirpath = os.path.join(tmp, "dir")
            gendir = os.path.join(dirpath, "gen")
            os.makedirs(gendir)
            with open(os.path.join(dirpath, "normal.py"), "w") as f:
                f.write("x = 1\n")
            with open(os.path.join(gendir, "ignored.py"), "w") as f:
                f.write("y = 2\n")

            forms = ["dir", "dir/", os.path.join(tmp, "dir")]
            script = (
                "import sys, re, json\n"
                "sys.path.insert(0, %r)\n"
                "from pylint.lint.expand_modules import expand_modules\n"
                "from pylint.utils import discover_package_path\n"
                "modules, errors = expand_modules([sys.argv[1]], [], [re.compile(sys.argv[2])], [])\n"
                "print(json.dumps([m['path'] for m in modules]))\n"
            ) % repo_root

            for form in forms:
                cwd = tmp
                proc = subprocess.run(
                    [sys.executable, "-c", script, form, ignore_pattern],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                leaked = "ignored.py" in proc.stdout
                status = "FAIL (leaked)" if leaked else "PASS"
                results.append(f"{form!r}: {status} stdout={proc.stdout.strip()!r} stderr={proc.stderr.strip()!r}")

        return "\n".join(results)
