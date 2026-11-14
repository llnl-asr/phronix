"""Contributing back up the chain: what a project learns about an upstream capability goes to that capability's home.

A project uses its upstream projects from clones in its own scope (``<project>/vendor/<upstream>``, installed
editable by its setup). The clone stays on its branch, because it is the code that runs. A change to a capability
another project owns is written into a *contribution worktree* of that clone instead:

    <project>/vendor/contrib/<upstream>     a git worktree of the clone, on branch contrib/<project>

and committed there. The project loads that worktree's capabilities over the clone's, so what it contributed is in
use immediately. :func:`update` keeps everything current: it fast-forwards each clone, rebases each contribution
branch on the upstream's default branch, and says what to push and where to open the pull request. Nothing is pushed
and no pull request is opened automatically: a person does that.

When an upstream is not a git checkout (installed from a wheel), contributions are exported to
``<project>/vendor/contrib-export/<upstream>/`` instead, to be applied in a clone by hand.
"""
from __future__ import annotations

import functools
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config as _cfg
from .scopes import Scope


def _git(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[-400:]}")
    return r


def repo_of(path: Path) -> Optional[Path]:
    """The git checkout ``path`` is in, or None (cached: a checkout does not move while a process runs)."""
    return _repo_of(str(Path(path)))


@functools.lru_cache(maxsize=256)
def _repo_of(path: str) -> Optional[Path]:
    p = Path(path)
    while not p.exists():
        p = p.parent
    r = _git(p if p.is_dir() else p.parent, "rev-parse", "--show-toplevel")
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def default_branch(repo: Path) -> str:
    r = _git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split("/", 1)[1]
    for b in ("develop", "main", "master"):
        if _git(repo, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{b}").returncode == 0:
            return b
    return _git(repo, "branch", "--show-current").stdout.strip() or "main"


def branch_name() -> str:
    return f"contrib/{_cfg.S.project}"


def _vendor() -> Path:
    root = _cfg.S.project_root or (_cfg.S.package_dir.parent if _cfg.S.package_dir else Path.cwd())
    return Path(root) / "vendor"


def worktree_path(scope: Scope) -> Path:
    return _vendor() / "contrib" / scope.project


def contrib_cap_dir(scope: Scope, create: bool = False) -> Optional[Path]:
    """The scope's capabilities directory in this project's contribution worktree (created when ``create``), or the
    export directory when the scope is not a git checkout; None when there is none yet and ``create`` is false."""
    repo = repo_of(scope.cap_dir)
    if repo is None:
        d = _vendor() / "contrib-export" / scope.project
        if create:
            d.mkdir(parents=True, exist_ok=True)
        return d if d.exists() else None
    wt = worktree_path(scope)
    rel = Path(os.path.relpath(scope.cap_dir.resolve(), repo.resolve()))
    if not (wt / ".git").exists():
        if not create:
            return None
        # From what the clone runs, so the worktree has every capability the clone has (it replaces the clone's
        # layer) and a contribution applies to the version in use; update() keeps it rebased on the clone.
        base = _git(repo, "rev-parse", "HEAD").stdout.strip() or "HEAD"
        wt.parent.mkdir(parents=True, exist_ok=True)
        exists = _git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch_name()}").returncode == 0
        args = ["worktree", "add", str(wt), branch_name()] if exists else ["worktree", "add", "-b", branch_name(), str(wt), base]
        _git(repo, *args, check=True)
    d = wt / rel
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def target_dir(scope: Scope, name: str, meta: Optional[dict] = None) -> Path:
    """Where capability ``name`` of ``scope`` is written in the contribution worktree: where it already is in that
    scope, else its topic (nested scopes) or its name."""
    from .scopes import find_bundles, topic_for
    base = contrib_cap_dir(scope, create=True)
    for b in find_bundles(base):
        if b.name == name:
            return b
    return base / topic_for(name, meta) / name if scope.nested else base / name


def commit_pending(message: str) -> List[Dict]:
    """Commit what was written into each contribution worktree. Returns {project, commit, branch} per commit."""
    out = []
    for scope in _cfg.S.upstream:
        repo = repo_of(scope.cap_dir)
        wt = worktree_path(scope)
        if repo is None or not (wt / ".git").exists():
            continue
        rel = os.path.relpath(scope.cap_dir.resolve(), repo.resolve())
        if not _git(wt, "status", "--porcelain", "--", rel).stdout.strip():
            continue
        _git(wt, "add", "-A", "--", rel, check=True)
        _git(wt, "commit", "-q", "-m", message, check=True)
        out.append({"project": scope.project, "branch": branch_name(),
                    "commit": _git(wt, "rev-parse", "--short", "HEAD").stdout.strip()})
    return out


def _pr_url(repo: Path, base: str) -> str:
    url = _git(repo, "remote", "get-url", "origin").stdout.strip()
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return f"https://github.com/{m.group(1)}/compare/{base}...{branch_name()}?expand=1" if m else ""


def _base(repo: Path) -> Tuple[str, str]:
    """(commit, branch) contributions build on: what the clone runs, and the branch it is on (the pull request's base)."""
    return (_git(repo, "rev-parse", "HEAD").stdout.strip(),
            _git(repo, "branch", "--show-current").stdout.strip() or default_branch(repo))


def update(pull: bool = True) -> Dict:
    """Bring every upstream clone up to date and rebase this project's contribution branches on them.

    Returns per upstream: the clone's state, the contribution branch (commits ahead of the default branch, whether the
    rebase succeeded) and, when there is something to contribute, the push command and the pull-request link."""
    report = {"project": _cfg.S.project, "upstream": []}
    for scope in _cfg.S.upstream:
        repo = repo_of(scope.cap_dir)
        item: Dict = {"project": scope.project, "clone": str(repo) if repo else None}
        if repo is None:
            exp = _vendor() / "contrib-export" / scope.project
            item["note"] = "installed from a package, not a clone: nothing to update"
            if exp.exists():
                item["export"] = str(exp)
            report["upstream"].append(item)
            continue
        if pull:
            f = _git(repo, "fetch", "-q", "origin")
            item["fetched"] = f.returncode == 0
            if f.returncode:
                item["fetch_error"] = (f.stderr or f.stdout).strip()[-300:]
            cur = _git(repo, "branch", "--show-current").stdout.strip()
            if cur and not _git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
                ff = _git(repo, "merge", "--ff-only", "-q", f"origin/{cur}")
                item["clone_updated"] = ff.returncode == 0
                if ff.returncode:
                    item["clone_note"] = f"{cur} has diverged from origin/{cur}: not fast-forwarded"
            else:
                item["clone_note"] = "the clone has local changes or no branch: left as it is"
        base_sha, base = _base(repo)
        wt = worktree_path(scope)
        if (wt / ".git").exists():
            rb = _git(wt, "rebase", base_sha)
            if rb.returncode:
                _git(wt, "rebase", "--abort")
                item["rebase"] = "conflict"
                item["rebase_error"] = (rb.stderr or rb.stdout).strip()[-400:]
            else:
                item["rebase"] = "ok"
            ahead = _git(wt, "rev-list", "--count", f"{base_sha}..HEAD").stdout.strip()
            item["contribution"] = {"branch": branch_name(), "worktree": str(wt), "ahead": int(ahead or 0), "base": base,
                                    "commits": _git(wt, "log", "--oneline", f"{base_sha}..HEAD").stdout.strip().splitlines()}
            if int(ahead or 0):
                item["to_do"] = {"push": f"git -C {wt} push -u origin {branch_name()}" + (" --force-with-lease" if item.get("rebase") == "ok" else ""),
                                 "pull_request": _pr_url(repo, base)}
        report["upstream"].append(item)
    return report


def status() -> Dict:
    """What this project has contributed upstream and not yet merged. Reads only: no fetch, no rebase."""
    return {"project": _cfg.S.project,
            "upstream": [{"project": s.project, "contribution": _ahead(s)} for s in _cfg.S.upstream]}


def _ahead(scope: Scope) -> Dict:
    repo, wt = repo_of(scope.cap_dir), worktree_path(scope)
    if repo is None or not (wt / ".git").exists():
        return {"ahead": 0}
    base_sha, base = _base(repo)
    commits = _git(wt, "log", "--oneline", f"{base_sha}..HEAD").stdout.strip().splitlines()
    return {"branch": branch_name(), "worktree": str(wt), "ahead": len(commits), "commits": commits, "base": base,
            "pull_request": _pr_url(repo, base) if commits else ""}
