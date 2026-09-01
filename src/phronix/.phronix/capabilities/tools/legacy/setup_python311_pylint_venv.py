import subprocess
import sys
import os


def register(mcp):
    @mcp.tool()
    def setup_python311_pylint_venv(repo_path: str, venv_path: str = "") -> str:
        """Create (or reuse) a Python 3.11 venv at *venv_path* (default:
        <repo_path>/tmp/research/venv<node>), install astroid==2.11.5, py>=1.11,
        pytest, then `pip install -e <repo_path>` into it.

        Needed because astroid<2.15 does `import imp` (removed in Python 3.12+),
        so running the actual pylint CLI end-to-end requires an older
        interpreter when the ambient default venv is 3.12/3.13.

        Returns a JSON string: {"status": "ok"|"error", "venv_path", "python",
        "log"} where "python" is the path to the venv's python executable to
        use for subsequent CLI/pytest invocations.
        """
        import json

        if not venv_path:
            venv_path = os.path.join(repo_path, "tmp", "research", "venv<node>")

        log = []
        try:
            if not os.path.exists(venv_path):
                r = subprocess.run(
                    ["python3.11", "-m", "venv", venv_path],
                    capture_output=True, text=True, timeout=300,
                )
                log.append(r.stdout + r.stderr)
                if r.returncode != 0:
                    return json.dumps({
                        "status": "error", "venv_path": venv_path,
                        "python": "", "log": "\n".join(log),
                    })

            python = os.path.join(venv_path, "bin", "python")
            pip_cmds = [
                [python, "-m", "pip", "install", "-q", "-U", "pip"],
                [python, "-m", "pip", "install", "-q", "astroid==2.11.5", "py>=1.11", "pytest"],
                [python, "-m", "pip", "install", "-q", "-e", repo_path],
            ]
            for cmd in pip_cmds:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                log.append(r.stdout + r.stderr)
                if r.returncode != 0:
                    return json.dumps({
                        "status": "error", "venv_path": venv_path,
                        "python": python, "log": "\n".join(log),
                    })

            return json.dumps({
                "status": "ok", "venv_path": venv_path, "python": python,
                "log": "\n".join(log),
            })
        except Exception as exc:
            log.append(str(exc))
            return json.dumps({
                "status": "error", "venv_path": venv_path, "python": "",
                "log": "\n".join(log),
            })
