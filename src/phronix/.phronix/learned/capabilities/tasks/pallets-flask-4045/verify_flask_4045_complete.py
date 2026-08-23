import subprocess, sys

def register(mcp):
    @mcp.tool()
    def verify_flask_4045_complete(repo_root: str) -> str:
        """Run target tests/checks for flask-4045 dotted blueprint/endpoint validation and report PASS/FAIL."""
        results = []

        pytest_run = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-W", "ignore::DeprecationWarning",
             "tests/test_blueprints.py::test_route_decorator_custom_endpoint_with_dots", "-q"],
            cwd=repo_root, capture_output=True, text=True,
        )
        results.append(f"pytest test_route_decorator_custom_endpoint_with_dots: rc={pytest_run.returncode}\n{pytest_run.stdout[-1500:]}\n{pytest_run.stderr[-500:]}")

        check_script = (
            "import sys; sys.path.insert(0, 'src')\n"
            "import flask\n"
            "ok = True\n"
            "for n in ['a.b', 'a.b.c']:\n"
            "    try:\n"
            "        flask.Blueprint(n, n)\n"
            "        print('FAIL: no ValueError for', n); ok = False\n"
            "    except ValueError:\n"
            "        print('OK: ValueError raised for', n)\n"
            "sys.exit(0 if ok else 1)\n"
        )
        direct = subprocess.run([sys.executable, "-c", check_script], cwd=repo_root, capture_output=True, text=True)
        results.append(f"direct Blueprint name check: rc={direct.returncode}\n{direct.stdout}\n{direct.stderr}")

        overall = pytest_run.returncode == 0 and direct.returncode == 0
        results.append(f"OVERALL: {'PASS' if overall else 'FAIL'}")
        return "\n---\n".join(results)
