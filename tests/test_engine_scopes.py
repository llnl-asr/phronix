"""The capability engine across projects: bundles, ownership, and contributing back to the owning upstream."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from phronix.engine.scopes import Scope, find_bundles, owner


def git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, text=True).stdout.strip()


def bundle(d: Path, name: str, code: str = "def register(mcp):\n    pass\n") -> Path:
    c = d / name
    (c / "versions" / "v1").mkdir(parents=True)
    (c / "capability.json").write_text(json.dumps({"name": name, "version": 1, "tools": []}))
    (c / "tool.py").write_text(code)
    (c / "versions" / "v1" / "tool.py").write_text("old\n")
    (c / "LESSONS.md").write_text(f"# Lessons: {name}\n")
    return c


def test_a_bundle_is_one_capability_and_its_versions_are_not_capabilities(tmp_path):
    from phronix.layers import _capability_entries
    caps = tmp_path / "capabilities"
    bundle(caps / "workloads", "workload_a")
    (caps / "tools" / "general").mkdir(parents=True)
    (caps / "tools" / "general" / "single.py").write_text("def register(mcp):\n    pass\n")
    got = _capability_entries(caps)
    assert set(got) == {"workload_a.py", "single.py"}
    assert got["workload_a.py"] == caps / "workloads" / "workload_a" / "tool.py"
    assert [b.name for b in find_bundles(caps)] == ["workload_a"]


def test_new_writes_a_bundle_and_keeps_history_on_rewrite(tmp_path, monkeypatch):
    from phronix import capabilities
    monkeypatch.setenv("PHRONIX_PROJECT_ROOT", str(tmp_path))
    code = "def register(mcp):\n    @mcp.tool()\n    def probe_one(x: str) -> str:\n        return x\n"
    r = capabilities.new("probe_one", "echo", source=code)
    d = Path(r["dir"])
    assert r["status"] == "ok" and Path(r["file"]) == d / "tool.py"
    meta = json.loads((d / "capability.json").read_text())
    assert meta["tools"] == ["probe_one"] and meta["version"] == 1
    for f in ("SKILL.md", "LESSONS.md", "WORKED.md", "agent.json", "checks.json"):
        assert (d / f).is_file(), f
    r2 = capabilities.new("probe_one", "echo", source=code.replace("return x", "return x * 2"), overwrite=True)
    assert r2["status"] == "ok"
    meta = json.loads((d / "capability.json").read_text())
    assert meta["version"] == 2 and "return x\n" in (d / "versions" / "v1" / "tool.py").read_text()


def test_ownership_import_then_name_then_phronix():
    root = Scope("phronix", "phronix", Path("/x/p"), root=True)
    dft = Scope("dftracer-agents", "dftracer_agents", Path("/x/d"), prefixes=("dftracer_",))
    moi = Scope("moirai-agents", "moirai_agents", Path("/x/m"), prefixes=("prov_",))
    chain = [root, dft, moi]
    assert owner("prov_graph", "", chain) is moi
    assert owner("dftracer_install", "", chain) is dft
    assert owner("workload_ior", "", chain) is root
    # Where its imports resolve wins over its name: a dftracer_-named bridge written in moirai stays in moirai.
    assert owner("dftracer_bridge", "from moirai_agents.core import x\n", chain) is moi
    assert owner("workload_x", "import dftracer_agents.helpers\nimport moirai_agents\n", chain) is moi


@pytest.fixture()
def chain(tmp_path, monkeypatch):
    """An upstream repo (origin + this project's clone of it in vendor/), and this project, engine configured."""
    from phronix.engine import configure
    origin = tmp_path / "up.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(origin), str(seed)], check=True, capture_output=True)
    for repo in (seed,):
        git(repo, "config", "user.email", "t@example.org"); git(repo, "config", "user.name", "t")
    up_caps = seed / "src" / "uppkg" / ".agents" / "capabilities"
    bundle(up_caps, "workload_x")
    git(seed, "add", "-A"); git(seed, "commit", "-q", "-m", "init"); git(seed, "push", "-q", "origin", "HEAD:main")
    proj = tmp_path / "proj"
    clone = proj / "vendor" / "up"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
    git(clone, "config", "user.email", "t@example.org"); git(clone, "config", "user.name", "t")
    own = proj / "src" / "projpkg" / ".agents" / "capabilities"
    bundle(own, "proj_thing")
    monkeypatch.setenv("TPROJ_LEARNING_DIR", str(tmp_path / "learning"))
    for k in ("PROJECT_CAPABILITIES", "USER_CAPABILITIES", "BUNDLED_CAPABILITIES"):
        monkeypatch.delenv(f"TPROJ_{k}", raising=False)
    up = Scope("up", "uppkg", clone / "src" / "uppkg" / ".agents" / "capabilities", root=True)
    me = Scope("proj", "projpkg", own, prefixes=("proj_",))
    configure(project="proj", env_prefix="TPROJ", package_dir=proj / "src" / "projpkg", scope=me, upstream=[up],
              project_root=proj)
    yield {"origin": origin, "seed": seed, "clone": clone, "proj": proj, "own": own}
    from phronix.engine import config
    config.S.upstream, config.S.scope = [], None


def test_upstream_capabilities_load_below_the_projects_own(chain):
    from phronix.engine import capstore
    caps = capstore.all_caps()
    assert caps["workload_x"][0] == "up" and caps["proj_thing"][1] == chain["own"] / "proj_thing"


def test_a_lesson_on_an_upstream_capability_is_committed_in_the_clone_on_its_branch(chain):
    from phronix.engine import capstore, learning
    r = learning.add("workload_x", "use the big input", source="user")
    assert r["status"] == "applied" and r["contributed"][0]["branch"] == "main", r
    clone = chain["clone"]
    assert git(clone, "branch", "--show-current") == "main"                    # never leaves its branch
    lessons = clone / "src" / "uppkg" / ".agents" / "capabilities" / "workload_x" / "LESSONS.md"
    assert "use the big input" in lessons.read_text()
    assert "proj: lesson for workload_x" in git(clone, "log", "-1", "--format=%s")
    assert git(clone, "status", "--porcelain") == "" and not (chain["proj"] / "vendor" / "contrib").exists()
    capstore._State.fingerprint = ""
    assert capstore.all_caps()["workload_x"][1] == lessons.parent
    # The project's own capability is written where it is, and nothing is committed for it.
    r = learning.add("proj_thing", "own lesson", source="user")
    assert "contributed" not in r and "own lesson" in (chain["own"] / "proj_thing" / "LESSONS.md").read_text()


def test_pull_latest_replays_the_local_commits_on_origin(chain):
    from phronix.engine import learning, upstream
    learning.add("workload_x", "lesson one", source="user")
    (chain["seed"] / "README.md").write_text("upstream moved\n")
    git(chain["seed"], "add", "-A"); git(chain["seed"], "commit", "-q", "-m", "other"); git(chain["seed"], "push", "-q", "origin", "HEAD:main")
    item = upstream.update()["upstream"][0]
    assert item["rebase"] == "ok" and item["pulled"] == 1, item
    assert item["contribution"]["ahead"] == 1 and item["contribution"]["push_state"] == "not_pushed"
    assert (chain["clone"] / "README.md").read_text() == "upstream moved\n"
    assert git(chain["clone"], "branch", "--show-current") == "main"
    assert upstream.status()["upstream"][0]["contribution"]["ahead"] == 1


def test_a_validator_only_capability_names_its_predictor_in_another(chain):
    from phronix.engine import capstore
    # workload_x (upstream) has no tools; give the check a capability that has one.
    ok = capstore.check_pvc({"predictor": ["proj_thing.make"], "validator": ["judge"]}, ["judge"])
    assert ok == ["pvc names proj_thing.make: proj_thing has no tool make"]
    assert capstore.check_pvc({"predictor": ["nope.make"], "validator": ["judge"]}, ["judge"]) == \
        ["pvc names nope.make: there is no capability nope"]
    assert "a validator must be this capability's own tool" in " ".join(
        capstore.check_pvc({"predictor": ["judge"], "validator": ["proj_thing.x"]}, ["judge"]))


def _skill(d: Path, rules):
    (d / "SKILL.md").write_text("---\nname: x\n---\n## Rules\n" + "".join(f"- {r}\n" for r in rules) + "\n## Corrector\n- generated fix line for the corrector, ignored entirely\n")


def test_consolidation_reports_only_pairs_with_the_projects_own(chain):
    from phronix.engine import capstore, consolidate
    shared = ["always stage the dataset on lustre before the first measured run starts",
              "never compare runs with different node counts or different input decks"]
    up = chain["clone"] / "src" / "uppkg" / ".agents" / "capabilities"
    for n in ("workload_a", "workload_b"):
        bundle(up, n); _skill(up / n, shared)
    capstore._State.fingerprint = ""
    assert consolidate.capabilities() == []            # two upstream capabilities: upstream's to consolidate
    _skill(chain["own"] / "proj_thing", shared)
    pairs = {tuple(sorted(g["ids"])) for g in consolidate.capabilities()}
    assert pairs == {("proj_thing", "workload_a"), ("proj_thing", "workload_b")}


def test_standing_text_is_not_an_overlap_and_a_keep_is_committed_with_its_reason(chain):
    from phronix.engine import capstore, consolidate
    own = chain["own"]
    for n in ("proj_a", "proj_b", "proj_c", "proj_d"):
        bundle(own, n)
        _skill(own / n, [f"Predictor `{n}_recipe` renders the recipe and the validator rules on a proposed command list"])
    capstore._State.fingerprint = ""
    assert consolidate.capabilities() == []            # the same generated line, modulo the name, in four of them
    r = consolidate.keep(["proj_a", "proj_b"], "different on purpose")
    assert Path(r["file"]) == own.parent / "consolidation_keep.json"
    assert consolidate.decisions() == [{"ids": "proj_a|proj_b", "why": "different on purpose"}]


# ------------------------------------------------------------------------------- rebase, merge, push
def _upstream_commit(chain, rel, text, msg="upstream change"):
    f = chain["seed"] / "src" / "uppkg" / ".agents" / "capabilities" / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    git(chain["seed"], "add", "-A"); git(chain["seed"], "commit", "-q", "-m", msg)
    git(chain["seed"], "push", "-q", "-f", "origin", "HEAD:main")


def test_lessons_from_both_sides_merge_by_themselves(chain):
    from phronix.engine import learning, upstream
    learning.add("workload_x", "ours: use the big input", source="user")
    _upstream_commit(chain, "workload_x/LESSONS.md", "# Lessons: workload_x\n\n- [L-up] theirs: pin the compiler\n")
    r = upstream.update()["upstream"][0]
    assert r["rebase"] == "ok" and r["rebase_resolved"] == ["src/uppkg/.agents/capabilities/workload_x/LESSONS.md"], r
    text = (chain["clone"] / "src/uppkg/.agents/capabilities/workload_x/LESSONS.md").read_text()
    assert "theirs: pin the compiler" in text and "ours: use the big input" in text and "<<<<<<<" not in text


def test_only_the_local_commits_are_replayed_when_upstream_rewrote_history(chain):
    from phronix.engine import learning, upstream
    learning.add("workload_x", "ours: a lesson", source="user")
    git(chain["seed"], "commit", "-q", "--amend", "-m", "init, amended")
    git(chain["seed"], "push", "-q", "-f", "origin", "HEAD:main")
    r = upstream.update()["upstream"][0]
    assert r["rebase"] == "ok" and r["contribution"]["ahead"] == 1, r
    assert git(chain["clone"], "log", "--format=%s", "-2").splitlines() == ["proj: lesson for workload_x", "init, amended"]


def _code_conflict(chain):
    from phronix.engine import upstream
    d = upstream.target_dir(next(iter(__import__("phronix.engine.config", fromlist=["S"]).S.upstream)), "workload_x")
    (d / "tool.py").write_text("def register(mcp):\n    pass  # ours\n")
    upstream.commit_pending("proj: change workload_x code")
    _upstream_commit(chain, "workload_x/tool.py", "def register(mcp):\n    pass  # theirs\n")


def test_a_code_conflict_without_the_agent_leaves_the_clone_as_it_was(chain):
    from phronix.engine import upstream
    _code_conflict(chain)
    before = git(chain["clone"], "rev-parse", "HEAD")
    r = upstream.update(resolve=False)["upstream"][0]
    assert r["rebase"] == "conflict" and r["conflicts"] == ["src/uppkg/.agents/capabilities/workload_x/tool.py"]
    assert git(chain["clone"], "rev-parse", "HEAD") == before and "rebase" not in git(chain["clone"], "status")
    assert git(chain["clone"], "branch", "--show-current") == "main"


def test_the_agent_merges_a_code_conflict_and_push_makes_a_new_branch(chain, tmp_path):
    from phronix.engine import config, upstream
    agent = tmp_path / "fake-claude"            # stands in for Claude Code: keeps both sides, no markers
    agent.write_text("#!/bin/bash\nfor f in $(git diff --name-only --diff-filter=U); do\n"
                     "  { git show :2:$f; echo '    # and ours'; } > $f; git add $f; done\necho merged\n")
    agent.chmod(0o755)
    config.S.agent = lambda: str(agent)
    try:
        _code_conflict(chain)
        r = upstream.push()["upstream"][0]
    finally:
        config.S.agent = None
    assert r["rebase"] == "ok" and r["rebase_merged_by_agent"] == ["src/uppkg/.agents/capabilities/workload_x/tool.py"], r
    assert r["pushed"] is True and r["pushed_branch"].startswith("contrib/proj-") and r["switch_to"] == "main", r
    assert git(chain["origin"], "rev-parse", r["pushed_branch"]) == git(chain["clone"], "rev-parse", "HEAD")
    assert git(chain["clone"], "branch", "--show-current") == "main"            # the clone stays on its branch
    assert git(chain["origin"], "rev-parse", "main") != git(chain["clone"], "rev-parse", "HEAD")


def test_push_then_switch_returns_the_clone_to_origin(chain):
    from phronix.engine import learning, upstream
    learning.add("workload_x", "first lesson", source="user")
    r = upstream.refresh()["upstream"][0]
    assert r["push_state"] == "not_pushed" and r["next"] == "push", r
    # switching before pushing would lose the commit: refused
    assert "Push first" in upstream.switch_to_branch("up")["error"]
    p = upstream.push(resolve=False)["upstream"][0]
    assert p["pushed"] and p["pull_request"] == "" or "compare/main..." in p["pull_request"]
    r = upstream.refresh()["upstream"][0]
    assert r["push_state"] == "pushed" and r["next"].startswith("open the pull request"), r
    assert upstream.push(resolve=False)["upstream"][0]["pushed"] is False          # nothing new to push
    learning.add("workload_x", "second lesson", source="user")
    assert upstream.refresh()["upstream"][0]["push_state"] == "needs_push"
    p2 = upstream.push(resolve=False)["upstream"][0]
    assert p2["pushed"] and p2["pushed_branch"] != p["pushed_branch"] or p2["pushed"]
    s = upstream.switch_to_branch("up")
    assert s["status"] == "ok" and s["branch"] == "main", s
    assert git(chain["clone"], "rev-parse", "HEAD") == git(chain["clone"], "rev-parse", "origin/main")
    assert upstream.refresh()["upstream"][0]["next"] == "nothing"


def test_a_merged_pull_request_comes_back_with_the_next_pull(chain):
    from phronix.engine import learning, upstream
    learning.add("workload_x", "a lesson to merge", source="user")
    b = upstream.push(resolve=False)["upstream"][0]["pushed_branch"]
    git(chain["seed"], "fetch", "-q", "origin", b)
    git(chain["seed"], "merge", "-q", "--no-ff", "-m", "Merge pull request", "FETCH_HEAD")
    git(chain["seed"], "push", "-q", "origin", "HEAD:main")
    upstream.switch_to_branch("up")
    r = upstream.update()["upstream"][0]
    assert r["rebase"] in ("ok", "up_to_date") and r["contribution"]["ahead"] == 0, r
    assert "a lesson to merge" in (chain["clone"] / "src/uppkg/.agents/capabilities/workload_x/LESSONS.md").read_text()


def test_a_scope_with_an_integration_branch_stays_on_it_and_prs_go_there(chain):
    from phronix.engine import config, configure, learning, upstream
    from phronix.engine.scopes import Scope
    git(chain["seed"], "checkout", "-q", "-b", "develop")
    _upstream_commit(chain, "workload_x/WORKED.md", "# What worked: workload_x\n- on develop\n", "develop change")
    git(chain["seed"], "push", "-q", "origin", "develop")
    git(chain["clone"], "fetch", "-q", "origin")
    git(chain["clone"], "checkout", "-q", "-b", "feature", "origin/main")
    up = Scope("up", "uppkg", chain["clone"] / "src/uppkg/.agents/capabilities", root=True, branch="develop")
    configure(project="proj", env_prefix="TPROJ", package_dir=chain["proj"] / "src/projpkg", scope=config.S.scope,
              upstream=[up], project_root=chain["proj"])
    # on another branch: not pulled, Switch offered
    assert upstream.update()["upstream"][0]["rebase"] == "not_on_branch"
    row = {r["project"]: r for r in upstream.repos()["repos"]}["up"]
    assert "switch" in row["actions"] and row["on_integration_branch"] is False
    assert upstream.switch_to_branch("up")["branch"] == "develop"
    learning.add("workload_x", "a lesson for develop", source="user")
    st = upstream.status()["upstream"][0]["contribution"]
    assert st["branch"] == "develop" and st["ahead"] == 1
    p = upstream.push(resolve=False)["upstream"][0]
    assert p["pushed"] and p["switch_to"] == "develop"


def test_pull_all_fast_forwards_clean_checkouts_and_leaves_the_rest(chain):
    from phronix.engine import upstream
    _upstream_commit(chain, "workload_x/WORKED.md", "# What worked: workload_x\n- new upstream\n")
    rep = upstream.pull_all(include_self=False)
    clone = next(r for r in rep["repos"] if r["repo"] == str(chain["clone"]))
    assert clone["pulled"] == 1 and rep["pulled"] == 1
    _upstream_commit(chain, "workload_x/WORKED.md", "# What worked: workload_x\n- newer\n")
    (chain["clone"] / "src/uppkg/.agents/capabilities/workload_x/tool.py").write_text("# local edit\n")
    clone = next(r for r in upstream.pull_all(include_self=False)["repos"] if r["repo"] == str(chain["clone"]))
    assert not clone.get("pulled") and "uncommitted" in clone["note"]


def test_the_repositories_overview_and_per_repo_actions(chain):
    from phronix.engine import learning, upstream
    learning.add("workload_x", "a lesson", source="user")
    rows = {r["project"]: r for r in upstream.repos()["repos"]}
    assert rows["up"]["actions"] == ["pull", "push"] and rows["up"]["contribution"]["ahead"] == 1
    assert rows["up"]["contribution"]["push_state"] == "not_pushed"
    _upstream_commit(chain, "workload_x/WORKED.md", "# What worked: workload_x\n- newer\n")
    r = upstream.pull("up")
    assert r["rebase"] == "ok" and r["pulled"] == 1, r
    assert upstream.push(only="up")["upstream"][0]["pushed"] is True
    row = {r["project"]: r for r in upstream.repos(fetch=True)["repos"]}["up"]
    assert row["contribution"]["push_state"] == "pushed" and row["actions"] == ["pull", "push", "switch"]
    assert upstream.push(only="nope")["upstream"] == []
