"""python -m phronix.engine <command> --project <package> ...

    update  --bootstrap MODULE[:FN]   fast-forward the upstream clones, rebase this project's contribution branches,
                                      and print what to push and where to open each pull request
    status  --bootstrap MODULE[:FN]   what this project has contributed upstream and not yet merged (reads only)

``--bootstrap`` names what configures the engine for the project (e.g. ``dftracer_agents.capabilities:engine``,
``moirai_agents.core._engine``); without it the engine serves phronix itself, which has nothing upstream.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m phronix.engine", description=__doc__.splitlines()[0])
    p.add_argument("command", choices=("update", "status"))
    p.add_argument("--bootstrap", default="")
    a = p.parse_args(argv)
    if a.bootstrap:
        m, _, f = a.bootstrap.partition(":")
        mod = importlib.import_module(m)
        if f:
            getattr(mod, f)()
    from . import upstream
    r = upstream.update() if a.command == "update" else upstream.status()
    print(json.dumps(r, indent=1))
    todo = [u for u in r.get("upstream", []) if u.get("to_do") or (u.get("contribution") or {}).get("ahead")]
    for u in todo:
        t = u.get("to_do") or {}
        print(f"\n{u['project']}: {u['contribution']['ahead']} contribution commit(s) on {u['contribution']['branch']}", file=sys.stderr)
        if t.get("push"):
            print(f"  push it:            {t['push']}", file=sys.stderr)
        if t.get("pull_request") or u["contribution"].get("pull_request"):
            print(f"  open the PR:        {t.get('pull_request') or u['contribution'].get('pull_request')}", file=sys.stderr)
    return 1 if any(u.get("rebase") == "conflict" for u in r.get("upstream", [])) else 0


if __name__ == "__main__":
    sys.exit(main())
