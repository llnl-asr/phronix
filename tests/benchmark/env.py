"""Load the project's ``.env`` the way the stack launcher does.

``phronix_stack`` sources ``.env`` before starting anything, so a daemon it spawns
sees ``OPENAI_API_KEY``. The benchmark is a separate entry point and had no such
step, which meant it worked when invoked from a shell that happened to have the
key exported and failed identically-looking when invoked from one that did not.
Same project, same credential, two different answers depending on how you got
there — so it loads the file too.

Two rules, both about not making a credential leak easier:

* **Already-exported values win.** ``.env`` fills gaps; it never overwrites what
  the caller deliberately set. The opposite would silently override a key chosen
  for this specific run.
* **Values are never logged.** :func:`describe` reports presence and length only.
  A benchmark that prints the key into a run directory has published it to
  everyone the results are shared with.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

#: `export FOO=bar`, `FOO=bar`, `FOO="bar"` — the three spellings that appear in
#: a hand-maintained .env.
_LINE = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')


def find_env(start: Optional[Path] = None) -> Optional[Path]:
    """Nearest ``.env`` walking up from *start* (default: the project root)."""
    try:
        from phronix.layers import project_root

        base = Path(start) if start else (project_root() or Path.cwd())
    except Exception:
        base = Path(start) if start else Path.cwd()
    for directory in (base, *base.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def parse(path: Path) -> Dict[str, str]:
    """Parse a ``.env`` into a dict. Tolerant: a malformed line is skipped.

    Deliberately not a full shell parser — no command substitution, no sourcing.
    A .env that can execute is a .env that can be weaponised by anyone who can
    write to it, and the file exists to carry a handful of literals.
    """
    values: Dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _LINE.match(line)
        if not match:
            continue
        key, raw = match.group(1), match.group(2).strip()
        if raw[:1] == raw[-1:] and raw[:1] in ("'", '"') and len(raw) >= 2:
            raw = raw[1:-1]
        values[key] = raw
    return values


def load(path: Optional[Path] = None, override: bool = False) -> List[str]:
    """Merge ``.env`` into ``os.environ``. Returns the names it set.

    Names only — never values, because the return value ends up in logs.
    """
    env_path = Path(path) if path else find_env()
    if env_path is None:
        return []
    applied: List[str] = []
    for key, value in parse(env_path).items():
        if not value:
            continue
        if override or not os.environ.get(key):
            os.environ[key] = value
            applied.append(key)
    return applied


def describe(keys: Optional[List[str]] = None) -> Dict[str, str]:
    """Presence and length of the credentials that matter. Never the values."""
    wanted = keys or ["OPENAI_API_KEY"]
    return {
        key: (f"set ({len(os.environ[key])} chars)" if os.environ.get(key) else "MISSING")
        for key in wanted
    }
