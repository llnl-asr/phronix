"""Contributing back up the chain: what a project learns about an upstream capability goes to that capability's home.

A project uses each upstream (phronix, dftracer-agents) from a clone in its own scope (``<project>/vendor/<upstream>``,
installed editable by its setup). The clone always stays on the upstream's integration branch: ``develop`` for
dftracer-agents (the scope's ``branch``), else the remote's default branch.

* A change to an upstream capability (a lesson, a worked entry, a new version) is written in the clone and committed
  there, on that branch, as a local commit ahead of ``origin/<branch>`` (:func:`commit_pending`). The project uses it at
  once: the clone is what it runs.
* **Pull latest** (:func:`pull`, :func:`update`): fetch, then replay the local commits on ``origin/<branch>``. Conflicts
  in lesson and worked logs and in capability.json merge by themselves; any other conflict goes to the agent (Claude
  Code, run in the clone), whose merge must leave no conflict markers and parse, else the rebase is aborted and the
  clone is as it was.
* **Push** (:func:`push`): pull latest, then push the local commits on a branch made only now,
  ``contrib/<project>-<date-time>``. The clone stays on ``<branch>``. The result carries the pull request's link.
* **Switch to develop** (:func:`switch_to_branch`): after a push, reset the clone to ``origin/<branch>``. The pushed
  commits live on the pushed branch; once its pull request is merged they come back with the next pull.

Nothing is pushed unless a person (or an agent asked to) calls :func:`push`; no pull request is opened automatically.
"""
from __future__ import annotations

import ast
import functools
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config as _cfg
from .scopes import Scope


def _git(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_EDITOR": "true"})
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


def integration_branch(repo: Path, scope: Optional[Scope] = None) -> str:
    """The branch the clone stays on and pull requests go to: the scope's ``branch`` (develop for dftracer-agents),
    else the remote's default branch."""
    return (scope.branch if scope is not None and scope.branch else "") or default_branch(repo)


def branch_name() -> str:
    """The prefix of the branches pushed for this project's contributions: contrib/<project>-<date-time>."""
    return f"contrib/{_cfg.S.project}"


def _counts(repo: Path, a: str, b: str) -> Tuple[int, int]:
    """(commits in a not in b, commits in b not in a)."""
    out = _git(repo, "rev-list", "--left-right", "--count", f"{a}...{b}").stdout.split()
    return (int(out[0]), int(out[1])) if len(out) == 2 else (0, 0)


def _scopes(only: Optional[str] = None) -> List[Scope]:
    """The upstream scopes, or the one named ``only``."""
    return [s for s in _cfg.S.upstream if not only or s.project == only]


# ------------------------------------------------------------------------------- writing a contribution
def contrib_cap_dir(scope: Scope, create: bool = False) -> Optional[Path]:
    """Where contributions to ``scope`` are written: its capabilities directory in the clone."""
    if create:
        scope.cap_dir.mkdir(parents=True, exist_ok=True)
    return scope.cap_dir


def target_dir(scope: Scope, name: str, meta: Optional[dict] = None) -> Path:
    """Where capability ``name`` of ``scope`` is written, in the clone: where it already is, else under its topic
    (nested scopes) or its name."""
    from .scopes import find_bundles, topic_for
    base = scope.cap_dir
    for b in find_bundles(base):
        if b.name == name:
            return b
    return base / topic_for(name, meta) / name if scope.nested else base / name


def commit_pending(message: str) -> List[Dict]:
    """Commit what was written into each upstream clone's capabilities, on the branch the clone is on (its integration
    branch). Returns {project, branch, commit} per commit."""
    out = []
    for scope in _cfg.S.upstream:
        repo = repo_of(scope.cap_dir)
        if repo is None:
            continue
        rel = os.path.relpath(scope.cap_dir.resolve(), repo.resolve())
        if not _git(repo, "status", "--porcelain", "--", rel).stdout.strip():
            continue
        on = _git(repo, "branch", "--show-current").stdout.strip()
        if on != integration_branch(repo, scope):
            # a checkout someone is developing on (another branch): leave the change uncommitted for them
            out.append({"project": scope.project, "branch": on, "commit": "", "note": "not committed: the clone is "
                        f"not on {integration_branch(repo, scope)}"})
            continue
        _git(repo, "add", "-A", "--", rel, check=True)
        _git(repo, "commit", "-q", "--no-verify", "-m", message, "--", rel, check=True)
        out.append({"project": scope.project, "branch": _git(repo, "branch", "--show-current").stdout.strip(),
                    "commit": _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()})
    return out


def contributed_bundles(scope: Scope) -> List[Path]:
    """Contributions are committed in the clone itself, which is already served: nothing to lay over it."""
    return []


# ------------------------------------------------------------------------------- merging a conflicted rebase
CONFLICT_MARKERS = ("<<<<<<< ", ">>>>>>> ")
LINE_MERGED = ("LESSONS.md", "WORKED.md")
AGENT_TIMEOUT = int(os.environ.get("PHRONIX_MERGE_AGENT_TIMEOUT", "900"))


def _stage(repo: Path, n: int, f: str) -> Optional[str]:
    r = _git(repo, "show", f":{n}:{f}")
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


def _auto_merge(repo: Path, f: str) -> bool:
    """Resolve the conflicted file f deterministically when its kind allows: lesson and worked logs, capability.json.
    During a rebase stage 2 is upstream's side (what is replayed onto), stage 3 this project's commit."""
    name = Path(f).name
    ours, theirs = _stage(repo, 2, f), _stage(repo, 3, f)
    if ours is None or theirs is None:
        return False
    if name in LINE_MERGED:
        (repo / f).write_text(_merge_lines(ours, theirs))
    elif name == "capability.json":
        try:
            merged = _merge_meta(json.loads(_stage(repo, 1, f) or "{}"), json.loads(ours), json.loads(theirs))
        except ValueError:
            return False
        (repo / f).write_text(json.dumps(merged, indent=1) + "\n")
    else:
        return False
    _git(repo, "add", "--", f)
    return True


def _clean(repo: Path, f: str) -> Optional[str]:
    """Why file f is not a good merge yet (conflict markers, a Python or JSON file that does not parse), or None."""
    p = repo / f
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


AGENT_PROMPT = """You are resolving a git rebase conflict in {repo}: this project's local commits on {branch} are being
replayed on {upstream}'s newer {branch}. Conflicted files: {files}.
For each file: read the three versions (git show :1:<file> base, :2:<file> upstream's, :3:<file> this project's), then
write the file so it keeps BOTH sides' intent: upstream's newer content and this project's change on top. For lessons
and worked entries keep every entry; for code keep both changes working together; never drop upstream's work. Remove
every conflict marker. Then run `git add <file>` for each. Do not commit, do not run git rebase, do not touch other
files. Reply with one line per file saying what you kept."""


def _agent_resolve(repo: Path, files: List[str], upstream_name: str, branch: str) -> Dict:
    """Ask the agent (Claude Code, non-interactive, in the clone) to merge the conflicted files."""
    exe = _cfg.agent_bin()
    if not exe:
        return {"ok": False, "error": "no agent to merge with: set the project's Claude Code path (<P>_CLAUDE_BIN)"}
    prompt = AGENT_PROMPT.format(repo=repo, branch=branch, upstream=upstream_name, files=", ".join(files))
    cmd = [exe, "-p", prompt, "--permission-mode", "acceptEdits",
           "--allowedTools", "Read,Edit,Write,Bash(git show:*),Bash(git diff:*),Bash(git add:*),Bash(git status:*)"]
    try:
        r = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, timeout=AGENT_TIMEOUT,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": f"the agent did not finish: {type(e).__name__}: {e}"}
    bad = {f: why for f in files for why in [_clean(repo, f)] if why}
    if r.returncode or bad:
        return {"ok": False, "error": f"the agent's merge is not usable: {bad or (r.stderr or r.stdout)[-400:]}"}
    for f in files:
        _git(repo, "add", "--", f)
    return {"ok": True, "summary": (r.stdout or "").strip()[-1500:]}


def _in_rebase(repo: Path) -> bool:
    gitdir = Path(_git(repo, "rev-parse", "--git-dir").stdout.strip() or ".")
    gitdir = gitdir if gitdir.is_absolute() else repo / gitdir
    return (gitdir / "rebase-merge").exists() or (gitdir / "rebase-apply").exists()


def _rebase_onto(repo: Path, onto: str, upstream_name: str, branch: str, resolve: bool, max_steps: int = 500) -> Dict:
    """Replay the clone's local commits onto ``onto``, merging conflicts (see the module docstring)."""
    r = _git(repo, "rebase", onto)
    resolved, by_agent, steps = [], [], 0
    while _in_rebase(repo) and steps < max_steps:
        steps += 1
        files = [f for f in _git(repo, "diff", "--name-only", "--diff-filter=U").stdout.splitlines() if f]
        rest = [f for f in files if not _auto_merge(repo, f)]
        resolved += [f for f in files if f not in rest]
        if rest:
            if not resolve:
                _git(repo, "rebase", "--abort")
                return {"status": "conflict", "conflicts": rest, "resolved": resolved}
            a = _agent_resolve(repo, rest, upstream_name, branch)
            if not a["ok"]:
                _git(repo, "rebase", "--abort")
                return {"status": "conflict", "conflicts": rest, "resolved": resolved, "error": a["error"]}
            by_agent += rest
        c = _git(repo, "rebase", "--continue")
        if c.returncode and _in_rebase(repo) and not _git(repo, "diff", "--name-only", "--diff-filter=U").stdout.strip():
            _git(repo, "rebase", "--skip")       # the commit became empty: upstream already has it
    if _in_rebase(repo):
        _git(repo, "rebase", "--abort")
        return {"status": "error", "error": f"the rebase did not finish in {max_steps} steps"}
    if r.returncode and steps == 0:
        return {"status": "error", "error": (r.stderr or r.stdout).strip()[-400:]}
    return {"status": "ok", "resolved": resolved, "merged_by_agent": by_agent}


# ------------------------------------------------------------------------------- pull, push, switch
def _pull_repo(repo: Path, branch: str, upstream_name: str, resolve: bool, fetch: bool = True) -> Dict:
    """Pull latest into a clone that stays on ``branch``: fast-forward, or replay its local commits (merging)."""
    out: Dict = {"branch": branch}
    if fetch:
        f = _git(repo, "fetch", "-q", "--prune", "origin")
        if f.returncode:
            out["fetch_error"] = (f.stderr or f.stdout).strip()[-300:]
    cur = _git(repo, "branch", "--show-current").stdout.strip()
    out["on"] = cur or "(detached)"
    if cur != branch:
        out.update(status="not_on_branch",
                   note=f"the clone is on {cur or 'a detached HEAD'}, not {branch}: Switch to {branch} first")
        return out
    remote = f"origin/{branch}"
    if _git(repo, "rev-parse", "--verify", "-q", remote).returncode:
        out.update(status="no_remote_branch", note=f"no {remote}")
        return out
    if _git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        out.update(status="dirty", note="uncommitted changes in the clone: commit or discard them first")
        return out
    local, behind = _counts(repo, "HEAD", remote)
    out.update(local_commits=local, behind=behind)
    if not behind:
        out["status"] = "up_to_date"
        return out
    if not local:
        m = _git(repo, "merge", "--ff-only", "-q", remote)
        out.update(status="ok" if m.returncode == 0 else "error", pulled=behind if m.returncode == 0 else 0)
        return out
    rb = _rebase_onto(repo, remote, upstream_name, branch, resolve)
    out.update({k: v for k, v in rb.items() if v})
    if rb["status"] == "ok":
        out["pulled"] = behind
    return out


def update(pull: bool = True, resolve: bool = True, only: Optional[str] = None) -> Dict:
    """Pull latest for every upstream clone (or ``only`` one): its local contribution commits replayed on
    origin/<branch>, conflicts merged. Per upstream: ``rebase`` (ok, up_to_date, conflict, dirty, not_on_branch, ...),
    ``rebase_resolved``, ``rebase_merged_by_agent``, ``conflicts`` and ``contribution``."""
    rep: Dict = {"project": _cfg.S.project, "upstream": []}
    for sc in _scopes(only):
        repo = repo_of(sc.cap_dir)
        if repo is None:
            rep["upstream"].append({"project": sc.project, "note": "installed from a package, not a clone"})
            continue
        r = _pull_repo(repo, integration_branch(repo, sc), sc.project, resolve, fetch=pull)
        item: Dict = {"project": sc.project, "rebase": r.pop("status", None)}
        for k, v in r.items():
            item[f"rebase_{k}" if k in ("resolved", "merged_by_agent", "error") else k] = v
        item["contribution"] = _contribution(repo, sc)
        rep["upstream"].append(item)
    return rep


def rebase(scope: Scope, resolve: bool = True) -> Dict:
    """Pull latest for one upstream scope (see :func:`update`)."""
    got = update(pull=True, resolve=resolve, only=scope.project)["upstream"]
    return got[0] if got else {"project": scope.project, "rebase": "error", "rebase_error": "no such upstream"}


def pull(project: str, resolve: bool = True) -> Dict:
    """Pull latest for one repository: this project's own checkout (fast-forward only) or an upstream clone."""
    if project == _cfg.S.project:
        own = repo_of(_cfg.S.project_root) if _cfg.S.project_root else None
        return {"project": project, "repo": _ff(own) if own else {"note": "not a git checkout"}}
    if not _scopes(project):
        return {"project": project, "error": f"no upstream {project}"}
    return update(pull=True, resolve=resolve, only=project)["upstream"][0]


def _pushed_key() -> str:
    return f"contrib.{re.sub(r'[^A-Za-z0-9]', '', _cfg.S.project) or 'project'}.pushed"


def _pushed(repo: Path) -> List[str]:
    return [b for b in _git(repo, "config", "--get-all", _pushed_key()).stdout.split() if b]


def _pr_url(repo: Path, base: str, head: str) -> str:
    """The page that opens a pull request of ``head`` into ``base`` (GitHub remotes), or ""."""
    url = _git(repo, "remote", "get-url", "origin").stdout.strip()
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?/?$", url)
    return f"https://github.com/{m.group(1)}/compare/{base}...{head}?expand=1" if m else ""


def push(resolve: bool = True, only: Optional[str] = None) -> Dict:
    """Pull latest (merging), then push each clone's local contribution commits on a NEW branch,
    contrib/<project>-<date-time>, created only now; the clone stays on its integration branch. Per upstream:
    ``pushed``, ``pushed_branch``, ``pull_request`` (the link that opens it) and ``switch_to`` (Switch's branch)."""
    rep = update(pull=True, resolve=resolve, only=only)
    for item in rep["upstream"]:
        c = item.get("contribution") or {}
        if not c.get("unpushed"):
            item["pushed"] = False
            item["push_note"] = ("already pushed: open the pull request, then Switch to " + c.get("branch", "")
                                 if c.get("ahead") else "nothing to push")
            if c.get("pull_request"):
                item["pull_request"] = c["pull_request"]
            continue
        if item.get("rebase") not in ("ok", "up_to_date"):
            item["pushed"] = False
            item["push_note"] = f"not pushed: pull latest did not succeed ({item.get('rebase')})"
            continue
        repo = Path(c["path"])
        name = f"{branch_name()}-{time.strftime('%Y%m%d-%H%M%S')}"
        r = _git(repo, "push", "origin", f"HEAD:refs/heads/{name}")
        item["pushed"] = r.returncode == 0
        if r.returncode:
            item["push_error"] = (r.stderr or r.stdout).strip()[-400:]
            continue
        _git(repo, "fetch", "-q", "origin", f"+refs/heads/{name}:refs/remotes/origin/{name}")
        _git(repo, "config", "--add", _pushed_key(), name)
        item.update(pushed_branch=name, pull_request=_pr_url(repo, c["branch"], name), switch_to=c["branch"],
                    contribution=_contribution(repo, _scopes(item["project"])[0]))
    return rep


def _unpushed(repo: Path, remote: str) -> List[str]:
    """Local commits (in HEAD, not in ``remote``) that no pushed contribution branch contains, oldest first."""
    pushed = [f"origin/{b}" for b in _pushed(repo)
              if _git(repo, "rev-parse", "--verify", "-q", f"origin/{b}").returncode == 0]
    out = []
    for c in reversed(_git(repo, "rev-list", f"{remote}..HEAD").stdout.split()):
        if not any(_git(repo, "merge-base", "--is-ancestor", c, b).returncode == 0 for b in pushed):
            out.append(_git(repo, "log", "--oneline", "-1", c).stdout.strip())
    return out


def switch_to_branch(project: str, force: bool = False) -> Dict:
    """Switch an upstream clone back to its integration branch at origin (develop). Its local contribution commits
    leave the clone, which is safe once they are on a pushed branch (refused otherwise unless ``force``)."""
    sc = _scopes(project)
    if not sc:
        return {"project": project, "error": f"no upstream {project}"}
    repo = repo_of(sc[0].cap_dir)
    if repo is None:
        return {"project": project, "error": "installed from a package, not a clone"}
    branch = integration_branch(repo, sc[0])
    remote = f"origin/{branch}"
    _git(repo, "fetch", "-q", "--prune", "origin")
    if _git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        return {"project": project, "error": "uncommitted changes in the clone: commit or discard them first"}
    if _git(repo, "rev-parse", "--verify", "-q", remote).returncode:
        return {"project": project, "error": f"no {remote}"}
    unpushed = _unpushed(repo, remote) if _git(repo, "branch", "--show-current").stdout.strip() == branch else []
    if unpushed and not force:
        return {"project": project, "error": f"{len(unpushed)} local commit(s) are on no pushed branch: Push first",
                "unpushed": unpushed}
    if _git(repo, "branch", "--show-current").stdout.strip() != branch:
        if _git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}").returncode:
            _git(repo, "checkout", "-q", "-b", branch, remote, check=True)
        else:
            _git(repo, "checkout", "-q", branch, check=True)
            unpushed = _unpushed(repo, remote)          # the local branch may hold commits of its own
            if unpushed and not force:
                return {"project": project, "status": "switched", "branch": branch,
                        "error": f"now on {branch}, but it has {len(unpushed)} local commit(s) on no pushed branch: "
                                 "Push them, or Pull latest", "unpushed": unpushed}
    _git(repo, "reset", "-q", "--hard", remote, check=True)
    return {"project": project, "status": "ok", "branch": branch,
            "head": _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()}


# ------------------------------------------------------------------------------- what stands where
def _contribution(repo: Path, scope: Scope) -> Dict:
    branch = integration_branch(repo, scope)
    remote = f"origin/{branch}"
    c: Dict = {"path": str(repo), "branch": branch, "ahead": 0, "push_state": "nothing"}
    if _git(repo, "rev-parse", "--verify", "-q", remote).returncode:
        return c
    ahead, behind = _counts(repo, "HEAD", remote)
    unpushed = _unpushed(repo, remote) if ahead else []
    c.update(ahead=ahead, behind=behind, unpushed=len(unpushed),
             commits=_git(repo, "log", "--oneline", f"{remote}..HEAD").stdout.strip().splitlines()[:20],
             push_state=("nothing" if not ahead else "not_pushed" if len(unpushed) == ahead
                         else "needs_push" if unpushed else "pushed"))
    pushed = [b for b in _pushed(repo) if _git(repo, "rev-parse", "--verify", "-q", f"origin/{b}").returncode == 0]
    if pushed:
        c["pushed_branch"] = pushed[-1]
        c["pull_request"] = _pr_url(repo, branch, pushed[-1])
    c["can_switch"] = bool(ahead and not unpushed)
    return c


def status() -> Dict:
    """Each upstream clone's local contribution commits and where they stand. Reads only."""
    return {"project": _cfg.S.project,
            "upstream": [{"project": s.project, "contribution": _contribution(r, s) if r else {"ahead": 0}}
                         for s in _cfg.S.upstream for r in [repo_of(s.cap_dir)]]}


def refresh(only: Optional[str] = None) -> Dict:
    """Fetch every upstream (or ``only`` one) and report where it stands and what to do next (switch, pull latest,
    push, open the pull request, nothing). Changes nothing else."""
    rep: Dict = {"project": _cfg.S.project, "upstream": []}
    for sc in _scopes(only):
        repo = repo_of(sc.cap_dir)
        item: Dict = {"project": sc.project}
        if repo is None:
            item["note"] = "installed from a package, not a clone"
            rep["upstream"].append(item)
            continue
        item["fetched"] = _git(repo, "fetch", "-q", "--prune", "origin").returncode == 0
        branch = integration_branch(repo, sc)
        cur = _git(repo, "branch", "--show-current").stdout.strip()
        c = _contribution(repo, sc)
        item.update(on=cur or "(detached)", contribution=c, push_state=c.get("push_state"))
        if c.get("pull_request"):
            item["pull_request"] = c["pull_request"]
        item["next"] = (f"switch to {branch}" if cur != branch else "pull latest" if c.get("behind") else
                        "push" if c.get("unpushed") else f"open the pull request, then switch to {branch}"
                        if c.get("can_switch") else "nothing")
        rep["upstream"].append(item)
    return rep


def _checkout_info(repo: Path) -> Dict:
    br = _git(repo, "branch", "--show-current").stdout.strip()
    info = {"path": str(repo), "branch": br or "(detached)",
            "head": _git(repo, "rev-parse", "--short", "HEAD").stdout.strip(),
            "dirty": bool(_git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip())}
    if br and _git(repo, "rev-parse", "--verify", "-q", f"origin/{br}").returncode == 0:
        info["ahead"], info["behind"] = _counts(repo, "HEAD", f"origin/{br}")
    return info


def repos(fetch: bool = False) -> Dict:
    """Every code base this project runs, for the Repositories panel: this project's checkout, then each upstream
    clone (its branch, whether that is its integration branch, behind origin, local contribution commits, their push
    state and pull-request link). ``fetch`` asks the remotes first; otherwise it only reads."""
    rows: List[Dict] = []
    own = repo_of(_cfg.S.project_root) if _cfg.S.project_root else None
    if own is not None:
        if fetch:
            _git(own, "fetch", "-q", "--prune", "origin")
        rows.append({"project": _cfg.S.project, "role": "this project", "actions": ["pull"], **_checkout_info(own)})
    for sc in _cfg.S.upstream:
        repo = repo_of(sc.cap_dir)
        row: Dict = {"project": sc.project, "role": "upstream"}
        if repo is None:
            row.update(note="installed from a package, not a clone", actions=[])
            rows.append(row)
            continue
        if fetch:
            _git(repo, "fetch", "-q", "--prune", "origin")
        row.update(_checkout_info(repo))
        c = _contribution(repo, sc)
        row.update(contribution=c, integration_branch=c["branch"], on_integration_branch=row["branch"] == c["branch"])
        if c.get("pull_request"):
            row["pull_request"] = c["pull_request"]
        row["actions"] = ["pull", "push"] + (["switch"] if not row["on_integration_branch"] or c.get("can_switch") else [])
        rows.append(row)
    return {"project": _cfg.S.project, "repos": rows}


# ------------------------------------------------------------------------------- keeping the code bases current
def _ff(repo: Path) -> Dict:
    """Fetch, then fast-forward the checkout's branch to its origin when that is safe: no uncommitted changes to
    tracked files, a branch with an origin counterpart, and nothing local a fast-forward would have to merge."""
    out: Dict = {"repo": str(repo)}
    f = _git(repo, "fetch", "-q", "--prune", "origin")
    if f.returncode:
        out["error"] = (f.stderr or f.stdout).strip()[-300:]
        return out
    br = _git(repo, "branch", "--show-current").stdout.strip()
    out["branch"] = br
    if not br or _git(repo, "rev-parse", "--verify", "-q", f"origin/{br}").returncode:
        out["note"] = "no branch with an origin counterpart: left as it is"
        return out
    local, remote = _counts(repo, "HEAD", f"origin/{br}")
    out.update(behind=remote, ahead=local)
    if not remote:
        return out
    if _git(repo, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        out["note"] = f"{remote} new commit(s) not pulled: uncommitted changes"
        return out
    if local:
        out["note"] = f"{remote} new commit(s) not pulled: {local} local commit(s) (Pull latest replays them)"
        return out
    m = _git(repo, "merge", "--ff-only", "-q", f"origin/{br}")
    out["pulled"] = remote if m.returncode == 0 else 0
    if m.returncode:
        out["note"] = (m.stderr or m.stdout).strip()[-300:]
    return out


def pull_all(include_self: bool = True) -> Dict:
    """Keep the running code current: fast-forward this project's own checkout (include_self) and every upstream clone
    with nothing local (a clone with contribution commits is pulled by Pull latest, which merges). Never merges or
    rebases on its own."""
    repos_: List[Path] = []
    if include_self and _cfg.S.project_root is not None:
        own = repo_of(_cfg.S.project_root)
        if own is not None:
            repos_.append(own)
    for sc in _cfg.S.upstream:
        r = repo_of(sc.cap_dir)
        if r is not None and r not in repos_:
            repos_.append(r)
    pulls = [_ff(r) for r in repos_]
    return {"project": _cfg.S.project, "repos": pulls, "pulled": sum(p.get("pulled", 0) for p in pulls)}


_PULLER: Dict[str, object] = {}


def start_auto_pull(on_pull=None, include_self: bool = True) -> bool:
    """Start (once per process) a background thread that runs pull_all at once and then every <P>_AUTO_PULL_MINUTES
    (10); <P>_AUTO_PULL=0 turns it off. ``on_pull(report)`` is called after each round that pulled something (a server
    reloads what changed). Returns whether it is running."""
    import threading
    if _cfg.env("AUTO_PULL", "1") in ("0", "false", "no"):
        return False
    if _PULLER.get("thread") is not None:
        return True
    minutes = float(_cfg.env("AUTO_PULL_MINUTES", "10") or 10)

    def loop():
        while True:
            try:
                rep = pull_all(include_self=include_self)
                _PULLER["last"] = {"at": time.time(), **rep}
                if rep.get("pulled") and on_pull is not None:
                    on_pull(rep)
            except Exception as e:           # a bad round never stops the server, nor the next round
                _PULLER["last"] = {"at": time.time(), "error": f"{type(e).__name__}: {e}"}
            time.sleep(max(60.0, minutes * 60))

    t = threading.Thread(target=loop, name="phronix-auto-pull", daemon=True)
    _PULLER["thread"] = t
    t.start()
    return True


def last_pull() -> Dict:
    """The last automatic pull's report ({} before the first)."""
    return dict(_PULLER.get("last") or {})
