"""Console-script shim for the ``phronix_stack`` launcher.

The launcher itself is bash shipped as package data beside this module. Bash,
because its whole job is supervising daemons — pid files, ports, signals,
``tail -f`` — and that is what bash is for. This module exists only to make it
*installable*: ``pip install`` puts ``phronix_stack`` on ``PATH``, and packaging a
shell script as a console script requires a Python shim to exec it.

The shim resolves three things bash cannot reliably work out once the package is
installed as a wheel rather than run from a checkout:

``PHRONIX_STACK_BIN``
    The directory holding ``mlflow``, ``phronix-mcp-server`` and
    ``phronix-profile-collector``. This is the *environment running this shim* —
    a venv or conda env — not whatever ``python3`` happens to be first on ``PATH``
    inside the script.

    Derived from ``sys.prefix``, never from ``Path(sys.executable).resolve()``: a
    venv's ``bin/python`` is a symlink to the base interpreter, so resolving it
    walks straight out of the venv and returns a bin directory where none of
    these console scripts exist.

``PHRONIX_STACK_ROOT``
    The project root — the directory that owns ``.phronix/``. From an installed
    wheel the script's own location is ``site-packages/phronix/`` and says nothing
    about the user's project, so it is detected from the working directory.

``PHRONIX_STACK_CMD``
    How the user spelled the command, so printed help is copy-pasteable.

``os.execve`` rather than ``subprocess``: the launcher's exit status, its signal
handling and its ``tail -f`` should belong to the user's shell directly, with no
Python process loitering in between.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _script() -> Path:
    return Path(__file__).resolve().with_name("phronix_stack")


def _env_bin() -> Path:
    """The active environment's ``bin/`` directory."""
    candidate = Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin")
    return candidate if candidate.is_dir() else Path(sys.executable).parent


def _project_root() -> Path:
    """The project the stack should serve.

    Reuses the same detection the rest of phronix uses, so the stack and the
    library can never disagree about which project they are in — a disagreement
    that would show up as the daemons serving one store while the tools write to
    another.
    """
    try:
        from phronix.layers import project_root

        found = project_root()
        if found is not None:
            return found
    except Exception:
        pass
    return Path.cwd()


def main() -> None:
    script = _script()
    if not script.exists():
        sys.exit(f"phronix_stack: launcher missing at {script}")

    bash = shutil.which("bash") or "/bin/bash"
    env = os.environ.copy()
    env.setdefault("PHRONIX_STACK_BIN", str(_env_bin()))
    env.setdefault("PHRONIX_STACK_ROOT", str(_project_root()))
    env.setdefault("PHRONIX_STACK_CMD", Path(sys.argv[0]).name or "phronix_stack")

    # Package data is not guaranteed executable after install, so invoke the
    # interpreter explicitly rather than relying on the mode bit.
    os.execve(bash, [bash, str(script), *sys.argv[1:]], env)


if __name__ == "__main__":
    main()
