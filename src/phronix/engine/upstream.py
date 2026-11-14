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

import ast
import functools
import json
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
    """(commit, branch): what the clone runs (contributions are rebased on it) and the upstream's default branch (the
    pull request's base, whatever branch the clone happens to be on)."""
    return _git(repo, "rev-parse", "HEAD").stdout.strip(), default_branch(repo)


def update(pull: bool = True, resolve: bool = True) -> Dict:
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
            rb = rebase(scope, resolve=resolve)
            item["rebase"] = rb["status"]
            for k in ("resolved", "merged_by_agent", "conflicts", "error"):
                if rb.get(k):
                    item["rebase_" + k if k != "conflicts" else "conflicts"] = rb[k]
            ahead = _git(wt, "rev-list", "--count", f"{base_sha}..HEAD").stdout.strip()
            item["contribution"] = {"branch": branch_name(), "worktree": str(wt), "ahead": int(ahead or 0), "base": base,
                                    "commits": _git(wt, "log", "--oneline", f"{base_sha}..HEAD").stdout.strip().splitlines()}
            if int(ahead or 0):
                item["to_do"] = {"push": f"git -C {wt} push --force-with-lease -u origin {branch_name()}",
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


# ------------------------------------------------------------------------------- rebase, merge, push
CONFLICT_MARKERS = ("<<<<<<< ", ">>>>>>> ")
LINE_MERGED = ("LESSONS.md", "WORKED.md")


def _cfg_key() -> str:
    return f"contrib.{re.sub(r'[^A-Za-z0-9]', '', _cfg.S.project) or 'project'}.base"


def _recorded_base(repo: Path, wt: Path) -> str:
    """The commit this project's contributions sit on. Recorded at every rebase; for a branch from before that, the
    parent of the run of commits at the top whose subject starts with "<project>: " (every contribution commit does)."""
    r = _git(repo, "config", "--get", _cfg_key()).stdout.strip()
    if r and _git(wt, "merge-base", "--is-ancestor", r, "HEAD").returncode == 0:
        return r
    prefix = f"{_cfg.S.project}: "
    base = "HEAD"
    for line in _git(wt, "log", "--first-parent", "--format=%H %s", "-n", "500").stdout.splitlines():
        sha, _, subject = line.partition(" ")
        if not subject.startswith(prefix):
            return sha
        base = f"{sha}^"
    return _git(wt, "rev-parse", base).stdout.strip()


def _stage(wt: Path, n: int, f: str) -> Optional[str]:
    r = _git(wt, "show", f":{n}:{f}")
    return r.stdout if r.returncode == 0 else None


def _merge_lines(ours: str, theirs: str) -> str:
    """Upstream's entries in their order, then this project's new ones: lessons and worked entries are a log."""
    seen, out = set(), []
    for line in (ours.splitlines() + theirs.splitlines()):
        key = line.strip()
        if key and key in seen:
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def _merge_meta(base: dict, ours: dict, theirs: dict) -> dict:
    """capability.json: the union of both histories, the higher version (one more when both moved), and for any other
    key this project's value when only it changed it, upstream's otherwise."""
    out = dict(ours)
    for k, v in theirs.items():
        if k == "history":
            seen, hist = set(), []
            for h in (ours.get("history") or []) + (v or []):
                key = json.dumps(h, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    hist.append(h)
            out[k] = sorted(hist, key=lambda h: (h.get("version", 0), h.get("ts", 0)))
        elif k == "version":
            b, o, n = int(base.get("version") or 0), int(ours.get("version") or 0), int(v or 0)
            out[k] = max(o, n) + (1 if o > b and n > b and o == n else 0)
        elif base.get(k) == ours.get(k):
            out[k] = v
    return out


def _auto_merge(wt: Path, f: str) -> bool:
    """Resolve the conflicted file f deterministically when its kind allows: lesson and worked logs, capability.json."""
    name = Path(f).name
    ours, theirs = _stage(wt, 2, f), _stage(wt, 3, f)
    if ours is None or theirs is None:
        return False
    if name in LINE_MERGED:
        (wt / f).write_text(_merge_lines(ours, theirs))
    elif name == "capability.json":
        try:
            merged = _merge_meta(json.loads(_stage(wt, 1, f) or "{}"), json.loads(ours), json.loads(theirs))
        except ValueError:
            return False
        (wt / f).write_text(json.dumps(merged, indent=1) + "\n")
    else:
        return False
    _git(wt, "add", "--", f)
    return True


def _clean(wt: Path, f: str) -> Optional[str]:
    """Why file f is not a good merge yet (conflict markers, a Python or JSON file that does not parse), or None."""
    p = wt / f
    if not p.exists():
        return None
    try:
        text = p.read_text()
    except (OSError, UnicodeDecodeError):
        return None
    if any(line.startswith(CONFLICT_MARKERS) for line in text.splitlines()):
        return "conflict markers left"
    try:
        if f.endswith(".py"):
            ast.parse(text)
        elif f.endswith(".json"):
            json.loads(text)
    except (SyntaxError, ValueError) as e:
        return f"does not parse: {e}"
    return None


AGENT_PROMPT = """You are resolving a git rebase conflict in {wt}, on branch {branch}: this project's contributions to
{upstream} are being replayed on its newer version. Conflicted files: {files}.
For each file: read the three versions (git show :1:<file> base, :2:<file> upstream's, :3:<file> ours), then write the
file so it keeps BOTH sides' intent - upstream's newer content and this project's change on top. For lessons and
worked entries keep every entry; for code keep both changes working together; never drop upstream's work. Remove every
conflict marker. Then run `git add <file>` for each. Do not commit, do not run git rebase, do not touch other files.
Reply with one line per file saying what you kept."""


def _agent_resolve(wt: Path, files: List[str], upstream_name: str) -> Dict:
    """Ask the agent (Claude Code, non-interactive, in the worktree) to merge the conflicted files."""
    exe = _cfg.agent_bin()
    if not exe:
        return {"ok": False, "error": "no agent to merge with: set the project's Claude Code path (e.g. <P>_CLAUDE_BIN)"}
    prompt = AGENT_PROMPT.format(wt=wt, branch=branch_name(), upstream=upstream_name, files=", ".join(files))
    cmd = [exe, "-p", prompt, "--permission-mode", "acceptEdits",
           "--allowedTools", "Read,Edit,Write,Bash(git show:*),Bash(git diff:*),Bash(git add:*),Bash(git status:*)"]
    try:
        r = subprocess.run(cmd, cwd=str(wt), capture_output=True, text=True, timeout=AGENT_TIMEOUT,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": f"the agent did not finish: {type(e).__name__}: {e}"}
    bad = {f: why for f in files for why in [_clean(wt, f)] if why}
    if r.returncode or bad:
        return {"ok": False, "error": f"the agent's merge is not usable: {bad or (r.stderr or r.stdout)[-400:]}"}
    for f in files:
        _git(wt, "add", "--", f)
    return {"ok": True, "summary": (r.stdout or "").strip()[-1500:]}


AGENT_TIMEOUT = int(os.environ.get("PHRONIX_MERGE_AGENT_TIMEOUT", "900"))


def _in_rebase(wt: Path) -> bool:
    gitdir = Path(_git(wt, "rev-parse", "--git-dir").stdout.strip() or ".")
    gitdir = gitdir if gitdir.is_absolute() else wt / gitdir
    return (gitdir / "rebase-merge").exists() or (gitdir / "rebase-apply").exists()


def rebase(scope: Scope, resolve: bool = True, max_steps: int = 500) -> Dict:
    """Replay this project's contribution commits (only those: never the base they were made on) onto what the clone
    runs. Conflicts in lesson and worked logs and capability.json merge deterministically; any other conflict goes to the
    agent when ``resolve``, and its merge must leave no markers and parse. If a conflict cannot be merged the rebase is
    aborted and the branch is as it was. Returns {status: ok|up_to_date|conflict|error, resolved, merged_by_agent}."""
    repo, wt = repo_of(scope.cap_dir), worktree_path(scope)
    if repo is None or not (wt / ".git").exists():
        return {"status": "up_to_date", "note": "no contribution worktree"}
    if _in_rebase(wt):
        _git(wt, "rebase", "--abort")
    if _git(wt, "status", "--porcelain").stdout.strip():
        return {"status": "error", "error": f"{wt} has uncommitted changes: commit or discard them first"}
    base_sha = _base(repo)[0]
    old = _recorded_base(repo, wt)
    if old == base_sha:
        return {"status": "up_to_date"}
    env_git = ["-c", "core.editor=true"]
    r = _git(wt, *env_git, "rebase", "--onto", base_sha, old)
    resolved, by_agent = [], []
    steps = 0
    while _in_rebase(wt) and steps < max_steps:
        steps += 1
        files = [f for f in _git(wt, "diff", "--name-only", "--diff-filter=U").stdout.splitlines() if f]
        rest = [f for f in files if not _auto_merge(wt, f)]
        resolved += [f for f in files if f not in rest]
        if rest:
            if not resolve:
                _git(wt, "rebase", "--abort")
                return {"status": "conflict", "conflicts": rest, "resolved": resolved}
            a = _agent_resolve(wt, rest, scope.project)
            if not a["ok"]:
                _git(wt, "rebase", "--abort")
                return {"status": "conflict", "conflicts": rest, "resolved": resolved, "error": a["error"]}
            by_agent += rest
        c = _git(wt, *env_git, "rebase", "--continue")
        if c.returncode and _in_rebase(wt) and not _git(wt, "diff", "--name-only", "--diff-filter=U").stdout.strip():
            _git(wt, *env_git, "rebase", "--skip")      # the commit became empty: upstream already has it
    if _in_rebase(wt):
        _git(wt, "rebase", "--abort")
        return {"status": "error", "error": f"the rebase did not finish in {max_steps} steps"}
    if r.returncode and steps == 0:                     # failed before replaying anything (not a conflict)
        return {"status": "error", "error": (r.stderr or r.stdout).strip()[-400:]}
    _git(repo, "config", _cfg_key(), base_sha)
    return {"status": "ok", "resolved": resolved, "merged_by_agent": by_agent}


def push(resolve: bool = True) -> Dict:
    """Update the clones, rebase every contribution branch (merging conflicts as rebase does), then push the branches
    that have something to contribute. Returns update()'s report with, per upstream, ``pushed`` and ``pull_request``."""
    rep = update(pull=True, resolve=resolve)
    for item in rep["upstream"]:
        c = item.get("contribution") or {}
        if not c.get("ahead"):
            continue
        if item.get("rebase") not in ("ok", "up_to_date"):
            item["pushed"] = False
            item["push_note"] = "not pushed: the rebase did not succeed"
            continue
        wt = Path(c["worktree"])
        r = _git(wt, "push", "--force-with-lease", "-u", "origin", branch_name())
        item["pushed"] = r.returncode == 0
        if r.returncode:
            item["push_error"] = (r.stderr or r.stdout).strip()[-400:]
        else:
            item["pull_request"] = (item.get("to_do") or {}).get("pull_request", "")
    return rep
