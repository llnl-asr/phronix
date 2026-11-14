"""Contributing back up the capability chain: what this project learned about another project's capabilities.

Each upstream (phronix, dftracer-agents) runs from a clone in this project's vendor/, which always stays on the
upstream's integration branch (develop for dftracer-agents). A change to a capability the upstream owns is committed
there as a local commit. These tools show it, pull latest (replaying the local commits on origin, merging conflicts:
lesson and worked logs and capability.json by themselves, anything else by the agent), push the local commits on a new
branch contrib/<this project>-<date-time> made only at push time, and switch the clone back to origin's branch.
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
              "the agent cannot, merge the listed files by hand in the clone and pull again")
        ahead = (u.get("contribution") or {}).get("unpushed", 0)
        if "pushed" in u:
            c(f"{p}:pushed", u["pushed"] or not ahead, u.get("push_error") or u.get("push_note") or "pushed",
              "fix what push_error says (credentials, a branch someone else changed), then contrib_push again")
            c(f"{p}:pull_request", not u.get("pushed") or bool(u.get("pull_request")), u.get("pull_request") or "no link",
              "open the pull request from the pushed branch on the upstream's page")
    if not checks:
        return {"status": "pass", "checks": [{"check": "nothing_to_contribute", "ok": True, "detail": "no upstream changes", "fix": ""}]}
    return {"status": "pass" if all(x["ok"] for x in checks) else "fail", "checks": checks}


def register(mcp):
    @mcp.tool()
    def contrib_repos(fetch: bool = False) -> str:
        """Every code base this project runs: its own checkout and each upstream's clone (dftracer-agents, phronix), with
        its branch, whether that is the integration branch (develop), how far it is behind origin, uncommitted changes,
        and the local contribution commits (ahead, unpushed, push_state, pushed_branch, pull_request). ``fetch`` asks
        the remotes first. Use before pulling, pushing or switching one repository.

        Returns JSON ``repos``: [{project, role, actions, path, branch, ahead, behind, dirty, contribution, pull_request}]."""
        from phronix.engine import upstream
        return _report(upstream.repos(fetch=bool(fetch)))

    @mcp.tool()
    def contrib_status() -> str:
        """The local contribution commits in each upstream clone and where they stand. Reads only.

        Returns JSON ``upstream``: per project ``contribution`` {branch, ahead, unpushed, commits, push_state,
        pushed_branch, pull_request, can_switch}."""
        from phronix.engine import upstream
        return _report(upstream.status())

    @mcp.tool()
    def contrib_refresh(project: str = "") -> str:
        """Fetch and report where each upstream clone stands; changes nothing else.

        Use to check a push, or before deciding what to do. Returns JSON upstream: per project on (branch), push_state
        (nothing, not_pushed, needs_push, pushed), contribution, pull_request and next (switch to <branch>, pull latest,
        push, open the pull request then switch, nothing)."""
        from phronix.engine import upstream
        return _report(upstream.refresh(only=project or None))

    @mcp.tool()
    def contrib_rebase(merge_with_agent: bool = True, project: str = "") -> str:
        """Pull latest into the upstream clones: the local contribution commits are replayed on origin/<branch>.

        Use when the user asks to pull or rebase (project: one upstream, e.g. dftracer-agents; empty: all). Conflicts in
        LESSONS.md, WORKED.md and capability.json merge by themselves; any other file is merged by the agent
        (merge_with_agent) and must then parse and carry no conflict markers, else the rebase is aborted and the clone
        stays as it was. Returns JSON ``upstream``: per project rebase (ok, up_to_date, conflict, dirty, not_on_branch,
        error), rebase_resolved, rebase_merged_by_agent, conflicts, contribution."""
        from phronix.engine import upstream
        return _report(upstream.update(pull=True, resolve=bool(merge_with_agent), only=project or None))

    @mcp.tool()
    def contrib_push(merge_with_agent: bool = True, project: str = "") -> str:
        """Pull latest (as contrib_rebase), then push each clone's unpushed contribution commits on a new branch
        contrib/<this project>-<date-time>, made only now; the clone stays on its integration branch.

        Use when the user asks to push or to contribute back (project: one upstream; empty: all). Returns JSON
        ``upstream``: per project rebase, pushed, pushed_branch, push_error, pull_request (the link that opens the pull
        request: give it to the user) and switch_to (contrib_switch returns the clone there)."""
        from phronix.engine import upstream
        return _report(upstream.push(resolve=bool(merge_with_agent), only=project or None))

    @mcp.tool()
    def contrib_switch(project: str, force: bool = False) -> str:
        """Switch an upstream clone back to origin's integration branch (develop), dropping its local contribution
        commits from the clone. Refused while a commit is on no pushed branch (push first) unless ``force``.

        Use after contrib_push, once the user has the pull-request link. Returns JSON {project, status, branch, head}
        or {error, unpushed}."""
        from phronix.engine import upstream
        return _report(upstream.switch_to_branch(project, force=bool(force)))

    @mcp.tool()
    def contrib_check(report_json: str) -> dict:
        """Rule on a contrib_status / contrib_rebase / contrib_push report, deterministically: every clone pulled (ok
        or up to date), every clone with unpushed commits pushed, and each pushed one with its pull-request link.

        Returns {"status": "pass"|"fail"|"inconclusive", "checks": [{"check", "ok", "detail", "fix"}]}."""
        return contribution_verdict(report_json)
