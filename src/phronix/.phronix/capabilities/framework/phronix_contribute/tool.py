"""Contributing back up the capability chain: what this project learned about another project's capabilities.

A change to a capability another project owns (phronix, dftracer-agents) is committed on contrib/<this project> in a
worktree of that project's clone (vendor/contrib/<project>). These tools show it, rebase it on the project's newer
version (merging conflicts: lesson and worked logs and capability.json by themselves, anything else by the agent), and
push it for a pull request.
"""
from __future__ import annotations

import json


def _report(r: dict) -> str:
    return json.dumps(r, indent=1, default=str)


def contribution_verdict(report_json: str) -> dict:
    """The deterministic rules a contribution report must satisfy before a pull request is opened."""
    try:
        r = json.loads(report_json) if isinstance(report_json, str) else dict(report_json)
    except (TypeError, ValueError) as e:
        return {"status": "inconclusive", "checks": [{"check": "parse", "ok": False, "detail": str(e),
                                                      "fix": "pass the JSON contrib_status, contrib_rebase or contrib_push returned"}]}
    checks = []

    def c(name, ok, detail, fix):
        checks.append({"check": name, "ok": bool(ok), "detail": detail, "fix": "" if ok else fix})

    ups = r.get("upstream")
    if not isinstance(ups, list):
        return {"status": "inconclusive", "checks": [{"check": "shape", "ok": False, "detail": "no upstream list",
                                                      "fix": "pass the whole report"}]}
    for u in ups:
        p = u.get("project", "?")
        reb = u.get("rebase")
        if reb is not None:
            c(f"{p}:rebased", reb in ("ok", "up_to_date"), f"rebase {reb}: {u.get('conflicts') or u.get('rebase_error') or ''}",
              "call contrib_rebase again (the agent merges what is not a lesson, worked entry or capability.json); if "
              "the agent cannot, merge the listed files by hand in the worktree and rebase again")
        ahead = (u.get("contribution") or {}).get("ahead", 0)
        if "pushed" in u:
            c(f"{p}:pushed", u["pushed"] or not ahead, u.get("push_error") or u.get("push_note") or "pushed",
              "fix what push_error says (credentials, a branch someone else changed), then contrib_push again")
            c(f"{p}:pull_request", not u.get("pushed") or bool(u.get("pull_request")), u.get("pull_request") or "no link",
              "open the pull request from the branch on the upstream's page")
    if not checks:
        return {"status": "pass", "checks": [{"check": "nothing_to_contribute", "ok": True, "detail": "no upstream changes", "fix": ""}]}
    return {"status": "pass" if all(x["ok"] for x in checks) else "fail", "checks": checks}


def register(mcp):
    @mcp.tool()
    def contrib_status() -> str:
        """What this project has contributed to the projects upstream of it and not yet merged. Reads only.

        Use to see what is waiting before asking the user to open pull requests. Returns JSON with ``upstream``: per
        project ``contribution`` {branch, worktree, ahead (commits), commits, base, pull_request}."""
        from phronix.engine import upstream
        return _report(upstream.status())

    @mcp.tool()
    def contrib_rebase(merge_with_agent: bool = True) -> str:
        """Bring the upstream clones up to date and rebase this project's contribution branches on them.

        Use when the user asks to rebase, or when contrib_status shows a branch behind. Only the contribution commits
        are replayed. Conflicts in LESSONS.md, WORKED.md and capability.json merge by themselves; any other file is
        merged by the agent (merge_with_agent) and must then parse and carry no conflict markers - else the rebase is
        aborted and the branch stays as it was. Returns JSON ``upstream``: per project rebase (ok, up_to_date,
        conflict, error), rebase_resolved, rebase_merged_by_agent, conflicts, contribution, to_do {push, pull_request}."""
        from phronix.engine import upstream
        return _report(upstream.update(pull=True, resolve=bool(merge_with_agent)))

    @mcp.tool()
    def contrib_push(merge_with_agent: bool = True) -> str:
        """Rebase this project's contribution branches (as contrib_rebase) and push the ones with commits, for a pull request.

        Use when the user asks to push or to contribute back. Pushes contrib/<this project> to the upstream's origin
        (with --force-with-lease, since the branch is rebased). Returns JSON ``upstream``: per project rebase, pushed,
        push_error, pull_request (the link to open it); give the links to the user."""
        from phronix.engine import upstream
        return _report(upstream.push(resolve=bool(merge_with_agent)))

    @mcp.tool()
    def contrib_check(report_json: str) -> dict:
        """Rule on a contrib_status / contrib_rebase / contrib_push report, deterministically: every branch rebased (ok
        or up to date), every branch with commits pushed, and each pushed one with its pull-request link.

        Returns {"status": "pass"|"fail"|"inconclusive", "checks": [{"check", "ok", "detail", "fix"}]}."""
        return contribution_verdict(report_json)
