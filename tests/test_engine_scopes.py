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


def test_a_lesson_on_an_upstream_capability_is_committed_on_the_contribution_branch(chain):
    from phronix.engine import capstore, learning
    r = learning.add("workload_x", "use the big input", source="user")
    assert r["status"] == "applied" and r["contributed"][0]["branch"] == "contrib/proj", r
    wt = chain["proj"] / "vendor" / "contrib" / "up"
    assert git(wt, "branch", "--show-current") == "contrib/proj"
    lessons = wt / "src" / "uppkg" / ".agents" / "capabilities" / "workload_x" / "LESSONS.md"
    assert "use the big input" in lessons.read_text()
    assert "proj: lesson for workload_x" in git(wt, "log", "-1", "--format=%s")
    # The clone the project runs is untouched; the project now loads the worktree's copy.
    assert "big input" not in (chain["clone"] / "src/uppkg/.agents/capabilities/workload_x/LESSONS.md").read_text()
    assert git(chain["clone"], "status", "--porcelain") == ""
    capstore._State.fingerprint = ""
    assert capstore.all_caps()["workload_x"][1] == lessons.parent
    # The project's own capability is written where it is, and nothing is committed for it.
    r = learning.add("proj_thing", "own lesson", source="user")
    assert "contributed" not in r and "own lesson" in (chain["own"] / "proj_thing" / "LESSONS.md").read_text()


def test_update_rebases_the_contribution_and_says_how_to_open_the_pr(chain):
    from phronix.engine import learning, upstream
    learning.add("workload_x", "lesson one", source="user")
    # Someone else lands a change upstream.
    (chain["seed"] / "README.md").write_text("upstream moved\n")
    git(chain["seed"], "add", "-A"); git(chain["seed"], "commit", "-q", "-m", "other"); git(chain["seed"], "push", "-q", "origin", "HEAD:main")
    r = upstream.update()
    item = r["upstream"][0]
    assert item["rebase"] == "ok" and item["clone_updated"], item
    assert item["contribution"]["ahead"] == 1
    assert "push -u origin contrib/proj" in item["to_do"]["push"]
    wt = Path(item["contribution"]["worktree"])
    assert (wt / "README.md").read_text() == "upstream moved\n"          # rebased on top of it
    assert (chain["clone"] / "README.md").exists()                         # the clone fast-forwarded
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
