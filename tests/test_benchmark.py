"""The benchmark's measurement logic.

Containers, harnesses and the dataset are not exercised here — those need
network and a runtime. What IS exercised is everything that decides what the
numbers mean: slope fitting, reuse attribution, the ledger, and the comparison
verdict. That is the part where a subtle error produces a plausible-looking
result rather than a crash, which makes it the part worth pinning hardest.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.benchmark import metrics, tasks
from tests.benchmark.runner import Ledger, read_retrievals


def _task(order, resolved=True, tries=1, tokens=1000, repo="a/a",
          created=None, retrieved=None):
    result = metrics.TaskResult(
        instance_id=f"inst-{order}", repo=repo, arm="test", order=order,
        skills_created=list(created or []), skills_retrieved=list(retrieved or []))
    for i in range(tries):
        last = i == tries - 1
        result.attempts.append(metrics.Attempt(
            index=i + 1, resolved=resolved and last,
            tokens_input=tokens, tokens_output=0, steps=3))
    return result


class TestSlope:
    def test_a_rising_series_has_a_positive_slope(self):
        slope, _ = metrics.ols_slope([0, 0, 0, 1, 1, 1, 1, 1])
        assert slope > 0

    def test_a_flat_series_has_zero_slope(self):
        slope, _ = metrics.ols_slope([1] * 10)
        assert slope == pytest.approx(0.0, abs=1e-12)

    def test_a_falling_series_has_a_negative_slope(self):
        slope, _ = metrics.ols_slope([5, 4, 3, 2, 1])
        assert slope == pytest.approx(-1.0)

    def test_too_few_points_is_infinite_uncertainty_not_a_confident_zero(self):
        """Two points fit a line perfectly; reporting that as certain is the lie."""
        slope, stderr = metrics.ols_slope([0, 1])
        assert stderr == float("inf")

    def test_noisy_data_gives_an_interval_that_includes_zero(self):
        slope, stderr = metrics.ols_slope([1, 0, 1, 0, 1, 0, 1, 0])
        low, high = metrics.confidence_interval(slope, stderr)
        assert low < 0 < high

    def test_a_clean_trend_gives_an_interval_excluding_zero(self):
        slope, stderr = metrics.ols_slope([0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1])
        low, high = metrics.confidence_interval(slope, stderr)
        assert low > 0

    def test_rolling_windows_partition_the_series(self):
        windows = metrics.rolling([1.0] * 25, window=10)
        assert [(a, b) for a, b, _ in windows] == [(1, 10), (11, 20), (21, 25)]


class TestArmSummary:
    def test_results_are_ordered_by_task_order_not_completion(self):
        """A slope fitted to completion order measures scheduling, not learning."""
        out_of_order = [_task(2, resolved=True), _task(0, resolved=False),
                        _task(1, resolved=False), _task(3, resolved=True),
                        _task(4, resolved=True), _task(5, resolved=True)]
        summary = metrics.summarise_arm(out_of_order)
        assert summary["learning_rate"]["resolve_slope"] > 0

    def test_tokens_per_resolved_is_none_when_nothing_resolved(self):
        """Zero or infinity would both read as a measurement rather than undefined."""
        summary = metrics.summarise_arm([_task(i, resolved=False) for i in range(5)])
        assert summary["tokens_per_resolved"] is None
        assert summary["cost_per_resolved"] is None

    def test_tries_are_counted_across_attempts(self):
        summary = metrics.summarise_arm([_task(0, tries=3), _task(1, tries=1)])
        assert summary["tries_total"] == 4
        assert summary["tries_mean"] == pytest.approx(2.0)

    def test_a_task_resolved_on_the_last_try_counts_as_resolved(self):
        assert _task(0, resolved=True, tries=3).resolved is True

    def test_reuse_rate_counts_tasks_not_skills(self):
        results = [_task(0), _task(1), _task(2), _task(3)]
        results[1].skills_reused = ["a", "b", "c"]
        results[2].skills_reused = ["a"]
        summary = metrics.summarise_arm(results)
        assert summary["learning_rate"]["reuse_rate"] == pytest.approx(0.5)

    def test_empty_arm_summarises_without_crashing(self):
        assert metrics.summarise_arm([])["tasks"] == 0


class TestLedger:
    def test_a_skill_reused_by_a_later_task_counts(self):
        ledger = Ledger()
        ledger.record_creation("workload-x", order=0, repo="a/a")
        classified = ledger.classify(["workload-x"], order=5, repo="a/a")
        assert classified["reused"] == ["workload-x"]

    def test_a_skill_read_back_in_the_same_task_does_not_count(self):
        """Otherwise every task that wrote a skill would look like it learned."""
        ledger = Ledger()
        ledger.record_creation("workload-x", order=3, repo="a/a")
        assert ledger.classify(["workload-x"], order=3, repo="a/a")["reused"] == []

    def test_a_skill_from_a_later_task_does_not_count(self):
        ledger = Ledger()
        ledger.record_creation("workload-x", order=9, repo="a/a")
        assert ledger.classify(["workload-x"], order=4, repo="a/a")["reused"] == []

    def test_a_bundled_skill_never_counts_as_learned(self):
        """It shipped with the framework; counting it would make every arm 'learn'."""
        ledger = Ledger()
        assert ledger.classify(["phronix-self-learning"], order=5, repo="a/a")["reused"] == []

    def test_cross_repo_reuse_is_tracked_separately(self):
        ledger = Ledger()
        ledger.record_creation("general-lesson", order=0, repo="a/a")
        classified = ledger.classify(["general-lesson"], order=4, repo="b/b")
        assert classified["reused"] == ["general-lesson"]
        assert classified["cross_repo"] == ["general-lesson"]

    def test_same_repo_reuse_is_not_cross_repo(self):
        ledger = Ledger()
        ledger.record_creation("repo-specific", order=0, repo="a/a")
        classified = ledger.classify(["repo-specific"], order=4, repo="a/a")
        assert classified["cross_repo"] == []

    def test_the_first_writer_keeps_credit(self):
        """A skill amended later was still learned earlier."""
        ledger = Ledger()
        ledger.record_creation("s", order=1, repo="a/a")
        ledger.record_creation("s", order=7, repo="b/b")
        assert ledger.created_by["s"] == 1
        assert ledger.classify(["s"], order=4, repo="a/a")["reused"] == ["s"]


class TestRetrievalLog:
    def test_skills_are_read_in_first_seen_order_without_duplicates(self, tmp_path):
        log = tmp_path / "r.jsonl"
        log.write_text("\n".join(json.dumps(r) for r in [
            {"skills": ["b", "a"]}, {"skills": ["a", "c"]}]))
        assert read_retrievals(log) == ["b", "a", "c"]

    def test_a_missing_log_is_empty_not_an_error(self, tmp_path):
        assert read_retrievals(tmp_path / "nope.jsonl") == []

    def test_a_corrupt_line_is_skipped(self, tmp_path):
        """A truncated final line from a killed run must not lose the whole log."""
        log = tmp_path / "r.jsonl"
        log.write_text('{"skills": ["a"]}\n{"skills": ["b"\n')
        assert read_retrievals(log) == ["a"]

    def test_phronix_writes_the_log_when_enabled(self, tmp_path, monkeypatch,
                                                 isolated_layers):
        """The reuse metric depends on this being a measured fact, not scraped."""
        from phronix.skills import search

        log = tmp_path / "r.jsonl"
        monkeypatch.setenv("PHRONIX_RETRIEVAL_LOG", str(log))
        search("never load a whole skill")
        assert log.is_file()
        assert "phronix-context-economy" in read_retrievals(log) or read_retrievals(log)

    def test_retrieval_logging_is_off_by_default(self, tmp_path, monkeypatch,
                                                 isolated_layers):
        from phronix.skills import search

        monkeypatch.delenv("PHRONIX_RETRIEVAL_LOG", raising=False)
        search("never load a whole skill")   # must not raise, must write nothing
        assert not list(tmp_path.glob("*.jsonl"))


class TestComparison:
    def _summaries(self, learn_resolved, control_resolved, reuse=True):
        def arm(pattern, with_reuse):
            results = []
            for i, ok in enumerate(pattern):
                task = _task(i, resolved=ok)
                if with_reuse and i > 0 and ok:
                    task.skills_reused = ["learned-skill"]
                results.append(task)
            return metrics.summarise_arm(results)

        return {
            "opencode-phronix": arm(learn_resolved, reuse),
            "opencode-phronix-frozen": arm(control_resolved, False),
        }

    def test_learning_demonstrated_needs_slope_reuse_and_significance(self):
        rising = [False] * 8 + [True] * 12
        flat = [True, False] * 10
        verdict = metrics.compare(self._summaries(rising, flat))["verdict"]
        assert verdict in ("learning_demonstrated", "learning_suggested")

    def test_improvement_without_reuse_is_not_called_learning(self):
        """The whole point of the reuse metric: a slope alone is ordering luck."""
        rising = [False] * 8 + [True] * 12
        flat = [True, False] * 10
        result = metrics.compare(self._summaries(rising, flat, reuse=False))
        assert result["verdict"] == "improvement_unexplained"
        assert "not attributable to learning" in result["note"]

    def test_no_improvement_over_the_control_is_reported_as_no_learning(self):
        flat = [True, False] * 10
        result = metrics.compare(self._summaries(flat, flat))
        assert result["verdict"] == "no_learning"

    def test_a_missing_control_refuses_to_quote_a_learning_rate(self):
        summaries = {"opencode-phronix": metrics.summarise_arm(
            [_task(i, resolved=i > 5) for i in range(20)])}
        result = metrics.compare(summaries)
        assert result["verdict"] == "uncontrolled"
        assert "cannot be separated from task-ordering" in result["note"]

    def test_a_missing_learning_arm_is_no_data(self):
        assert metrics.compare({})["verdict"] == "no_data"


class TestPersistence:
    def test_results_round_trip(self, tmp_path):
        original = [_task(0, tries=2, created=["s1"]), _task(1, retrieved=["s1"])]
        original[1].skills_reused = ["s1"]
        path = metrics.write_results(tmp_path / "r.jsonl", original)
        loaded = metrics.read_results(path)
        assert [r.instance_id for r in loaded] == ["inst-0", "inst-1"]
        assert loaded[0].tries == 2
        assert loaded[1].skills_reused == ["s1"]

    def test_append_keeps_a_crashed_run(self, tmp_path):
        """A run killed at task 22 must keep 21 tasks, not zero."""
        path = tmp_path / "r.jsonl"
        for i in range(3):
            metrics.append_result(path, _task(i))
        assert len(metrics.read_results(path)) == 3

    def test_reading_a_missing_file_is_empty(self, tmp_path):
        assert metrics.read_results(tmp_path / "nope.jsonl") == []


class TestTaskFile:
    def test_order_is_preserved_and_comments_ignored(self, tmp_path):
        path = tmp_path / "t.txt"
        path.write_text("# header\n\nb-1\na-2\nc-3\n")
        assert tasks.read_task_file(path) == ["b-1", "a-2", "c-3"]

    def test_the_header_records_how_it_was_produced(self, tmp_path):
        """Without split and seed, a task list cannot be regenerated or justified."""
        path = tasks.write_task_file(tmp_path / "t.txt", ["x-1", "y-2"], "lite", 7)
        header = path.read_text()
        assert "seed 7" in header and "lite" in header and "checksum" in header

    def test_selection_is_reproducible_for_a_seed(self):
        instances = {f"repo{i % 4}__x-{i}": {"instance_id": f"repo{i % 4}__x-{i}",
                                             "repo": f"org/repo{i % 4}"}
                     for i in range(40)}
        first = tasks.select(instances, limit=12, seed=3)
        assert first == tasks.select(instances, limit=12, seed=3)
        assert first != tasks.select(instances, limit=12, seed=4)

    def test_stratification_spreads_across_repositories(self):
        """An unstratified Lite sample is mostly one codebase, which makes
        cross-repo reuse unobservable — and that is one of the metrics."""
        instances = {}
        for i in range(60):
            repo = "org/big" if i < 50 else f"org/small{i}"
            instances[f"i-{i}"] = {"instance_id": f"i-{i}", "repo": repo}
        chosen = tasks.select(instances, limit=10, seed=0, stratify=True)
        repos = {instances[i]["repo"] for i in chosen}
        assert len(repos) > 1

    def test_a_missing_task_file_is_a_clear_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            tasks.read_task_file(tmp_path / "nope.txt")


class TestIsolation:
    def test_image_name_encodes_the_instance_id_safely(self):
        """`__` is not legal in a docker tag; SWE-bench's convention is `_1776_`."""
        from tests.benchmark.isolation import image_for

        assert image_for("astropy__astropy-12907").endswith(
            "sweb.eval.x86_64.astropy_1776_astropy-12907:latest")

    def test_fresh_store_contains_the_skeleton_and_nothing_else(self, tmp_path):
        from tests.benchmark.isolation import fresh_store, store_inventory

        store = fresh_store(tmp_path / ".phronix")
        inventory = store_inventory(store)
        assert "phronix-self-learning" in inventory["skills"]
        assert inventory["memory"] == []          # no learned memories
        assert inventory["capabilities"] == []    # no learned capabilities

    def test_fresh_store_wipes_a_previous_run(self, tmp_path):
        from tests.benchmark.isolation import fresh_store, store_inventory

        store = tmp_path / ".phronix"
        fresh_store(store)
        (store / "skills" / "leaked-from-last-run").mkdir(parents=True)
        fresh_store(store)
        assert "leaked-from-last-run" not in store_inventory(store)["skills"]

    def test_isolated_env_redirects_every_layer(self, tmp_path):
        """PHRONIX_HOME in particular: without it the developer's own ~/.phronix
        skills are merged in and silently pre-train the run."""
        from tests.benchmark.isolation import isolated_env

        env = isolated_env(tmp_path / "p" / ".phronix", tmp_path / "cache")
        assert env["PHRONIX_HOME"].startswith(str(tmp_path))
        assert env["PHRONIX_CACHE"].startswith(str(tmp_path))
        assert env["PHRONIX_PROJECT_ROOT"].startswith(str(tmp_path))

    def test_frozen_arm_mounts_the_store_read_only(self):
        """A control that *could* write is not a control."""
        from tests.benchmark.arms import PhronixArm, PhronixFrozenArm

        frozen = PhronixFrozenArm().mounts(Path("/store"))
        live = PhronixArm().mounts(Path("/store"))
        assert any(str(v).endswith(":ro") for v in frozen.values())
        assert not any(str(v).endswith(":ro") for v in live.values())

    def test_the_bare_arm_mounts_no_store(self):
        from tests.benchmark.arms import OpenCodeArm

        assert OpenCodeArm().mounts(Path("/store")) == {}


class TestArmConfiguration:
    def test_every_arm_uses_the_same_model(self):
        """The comparison is void if the arms differ in the model they run.

        Checked per harness, because the two spell the same model differently:
        opencode qualifies it with a provider, Claude Code names it directly.
        What must not vary is the model itself — an arm quietly on a stronger
        one would look like the framework working.
        """
        from tests.benchmark.arms import ARM_ORDER, build

        by_harness = {}
        for name in ARM_ORDER:
            arm = build(name)
            harness = "claude" if name.startswith("claude") else "opencode"
            by_harness.setdefault(harness, set()).add(arm.qualified_model)

        assert by_harness["opencode"] == {"livai/claude-sonnet-4.5"}
        assert by_harness["claude"] == {"claude-sonnet-4.5"}

        # Same model underneath, whatever the harness calls it.
        bare = {m.split("/")[-1] for names in by_harness.values() for m in names}
        assert len(bare) == 1, bare

    def test_a_missing_api_key_fails_before_the_run_starts(self, monkeypatch):
        """Better than discovering it 30 tasks in, where it looks like a bug."""
        from tests.benchmark.arms import model_env

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            model_env()

    def test_an_unknown_arm_is_rejected_by_name(self):
        from tests.benchmark.arms import build

        with pytest.raises(KeyError, match="unknown arm"):
            build("not-an-arm")

    def test_the_baseline_survives_the_shared_generate_path(self, tmp_path,
                                                            monkeypatch):
        """The baseline must run every line of `generate` the phronix arms do.

        Twice now a phronix-only attribute was referenced from the SHARED
        opencode path, and both times the baseline raised before its agent
        started — reporting `0 steps, 0 tokens` for every task, which reads as an
        agent that did nothing rather than a harness that never called one. A
        crash that silently becomes a plausible benchmark result is worth a test.
        """
        import subprocess
        from tests.benchmark import arms as arms_module
        from tests.benchmark.arms import build

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        launched = {}

        def fake_run(command, *args, **kwargs):
            launched["command"] = command

            class Result:
                returncode, stdout, stderr = 0, "", ""

            return Result()

        monkeypatch.setattr(subprocess, "run", fake_run)

        class FakeRuntime:
            def run(self, *args, **kwargs):
                class Result:
                    returncode, stdout, stderr = 0, "", ""

                return Result()

        class FakeContainer:
            name, runtime = "c", FakeRuntime()

        workdir = tmp_path / "attempt-1"
        (workdir / "repo").mkdir(parents=True)
        store = tmp_path / "store" / ".phronix"
        store.mkdir(parents=True)

        for name in ("opencode-bare", "opencode-phronix"):
            arm = build(name)
            outcome = arm.generate({"instance_id": "repo__repo-1",
                                    "problem_statement": "an issue"},
                                   store, workdir, FakeContainer())
            assert outcome.error == "", f"{name}: {outcome.error}"
            assert launched["command"], f"{name} never launched an agent"

    def test_every_arm_has_what_the_runner_reaches_for(self):
        """Whatever the runner touches on an arm, every arm must have.

        Three separate crashes reached a live run this way — `research_topic`,
        `research_spent`, `research_budget_s` — each an attribute added for the
        phronix arms and then referenced from shared code. They all present
        identically: the attempt raises before its agent starts and the task is
        recorded as `0 steps, 0 tokens`, which is indistinguishable from an agent
        that ran and did nothing. Reading the runner for `arm.<name>` and
        checking it against every arm is cheap and catches the whole class.
        """
        import re
        from pathlib import Path
        from tests.benchmark.arms import ARM_ORDER, build

        source = Path("tests/benchmark/runner.py").read_text()
        used = sorted(set(re.findall(r"\barm\.([a-zA-Z_][a-zA-Z0-9_]*)", source)))
        assert used, "found no arm attribute references — has the runner moved?"

        for name in ARM_ORDER:
            arm = build(name)
            missing = [attribute for attribute in used
                       if not hasattr(arm, attribute)]
            # mini brings its own sandbox, so the checkout helpers never apply.
            if arm.generates_own_environment:
                missing = [m for m in missing if m != "prepare_checkout"]
            assert not missing, f"{name} is missing {missing}"

    def test_arm_order_reads_as_the_argument(self):
        """reference, baseline, control, claim — then the same pair again on the
        second harness, so a reader sees which comparison each belongs to."""
        from tests.benchmark.arms import ARM_ORDER

        assert ARM_ORDER == ["mini", "opencode-bare",
                             "opencode-phronix-frozen", "opencode-phronix",
                             "claude-bare", "claude-phronix"]


class TestReport:
    def test_a_run_directory_renders(self, tmp_path):
        from tests.benchmark import report

        for arm, pattern in (("opencode-phronix", [False] * 6 + [True] * 8),
                             ("opencode-phronix-frozen", [True, False] * 7)):
            arm_dir = tmp_path / arm
            arm_dir.mkdir()
            results = []
            for i, ok in enumerate(pattern):
                task = _task(i, resolved=ok)
                task.arm = arm
                if arm == "opencode-phronix" and i > 2:
                    task.skills_reused = ["s"]
                results.append(task)
            metrics.write_results(arm_dir / "results.jsonl", results)
        (tmp_path / "manifest.json").write_text(json.dumps(
            {"model": "claude-sonnet-4.5", "provider": "livai", "tasks": ["x"] * 14}))

        rendered = report.render(report.build(tmp_path))
        assert "## Verdict" in rendered
        assert "opencode-phronix" in rendered
        assert "95% CI" in rendered or "CI" in rendered

    def test_report_files_are_written(self, tmp_path):
        from tests.benchmark import report

        arm_dir = tmp_path / "opencode-bare"
        arm_dir.mkdir()
        metrics.write_results(arm_dir / "results.jsonl", [_task(i) for i in range(4)])
        written = report.write(tmp_path)
        assert written["markdown"].is_file() and written["json"].is_file()


class TestCli:
    def test_the_parser_exposes_the_three_subcommands(self):
        from tests.benchmark.cli import build_parser

        parser = build_parser()
        for argv in (["tasks"], ["run"], ["report", "x"]):
            assert parser.parse_args(argv).command == argv[0]

    def test_run_defaults_to_all_four_arms(self):
        from tests.benchmark.arms import ARM_ORDER
        from tests.benchmark.cli import build_parser

        args = build_parser().parse_args(["run"])
        assert args.arms.split(",") == ARM_ORDER

    def test_an_unknown_arm_is_rejected_before_spending_anything(self, capsys):
        from tests.benchmark.cli import main

        assert main(["run", "--arms", "nonsense", "--tasks", "/nonexistent"]) == 1


def test_django_instances_use_runtests_not_bare_pytest():
    """Django's suite cannot be started by pytest, so it must not be.

    Every Django test file imports `django.contrib.*` at module scope, which
    reads `settings.INSTALLED_APPS` — so under plain pytest each file dies at
    COLLECTION with `ImproperlyConfigured`, before one test runs. Measured on
    django__django-13551: the agent produced the upstream fix byte for byte and
    the run scored it 0/2 target and 0/56 pass-to-pass, which is indexed as a
    catastrophically wrong patch rather than as a suite that never started.
    """
    from tests.benchmark.runner import _needs_django_runner, _django_labels

    assert _needs_django_runner({"repo": "django/django"})
    assert not _needs_django_runner({"repo": "sympy/sympy"})

    # runtests.py takes dotted labels, never file paths.
    labels = _django_labels(
        ["test_token_with_different_secret (auth_tests.test_tokens.TokenGeneratorTest)"],
        ["tests/auth_tests/test_models.py"])
    assert labels == ["auth_tests.test_tokens", "auth_tests.test_models"]

    # Fixture modules the test patch happens to touch are not test labels, and
    # handing them to runtests.py risks taking the whole invocation down.
    assert _django_labels([], ["tests/auth_tests/test_tokens.py",
                               "tests/auth_tests/models/__init__.py",
                               "tests/auth_tests/models/with_custom_email_field.py"]) \
        == ["auth_tests.test_tokens"]


def test_django_results_are_read_in_both_shapes_swe_bench_stores():
    """A passing test contributes its node id AND its docstring.

    unittest at verbosity 2 prints the docstring instead of the id when a test
    has one, and SWE-bench stores whichever form it saw — django-13551 lists
    one target as `test_token_with_different_secret (...)` and the other as
    "Updating the user email address invalidates the token." Matching only one
    shape scores a passing test as failed because of how the dataset happened
    to name it.
    """
    from tests.benchmark.runner import _django_any_test_ran, _django_passed_ids

    output = (
        "test_make_token (auth_tests.test_tokens.TokenGeneratorTest) ... ok\n"
        "test_check (auth_tests.test_tokens.TokenGeneratorTest)\n"
        "Updating the user email address invalidates the token. ... ok\n"
        "test_timeout (auth_tests.test_tokens.TokenGeneratorTest)\n"
        "The token is valid after n seconds, but no greater. ... FAIL\n"
        "test_broken (auth_tests.test_models.UserTest) ... ERROR\n"
        "----------------------------------------------------------------------\n"
        "Ran 4 tests in 0.1s\n")

    passed = _django_passed_ids(output)
    assert "test_make_token (auth_tests.test_tokens.TokenGeneratorTest)" in passed
    assert "Updating the user email address invalidates the token." in passed
    # A failure contributes neither shape — not its id and not its docstring.
    assert "test_timeout (auth_tests.test_tokens.TokenGeneratorTest)" not in passed
    assert "The token is valid after n seconds, but no greater." not in passed
    assert "test_broken (auth_tests.test_models.UserTest)" not in passed

    assert _django_any_test_ran(output)
    # The failure this whole path exists to catch: a suite that never started
    # must read as a runner fault, not as every test failing.
    assert not _django_any_test_ran(
        "ImproperlyConfigured: Requested setting INSTALLED_APPS, but settings "
        "are not configured.")


def test_baseline_cache_is_ignored_when_the_runner_changed(tmp_path, monkeypatch):
    """A baseline is only valid for the runner that measured it.

    Nothing recorded how a cached baseline was produced, so when Django moved
    from bare pytest to `runtests.py` the stored entries stayed authoritative —
    and they had been measured while the suite could not start, claiming 56
    pass-to-pass tests were already broken when every one of them passes. A
    stale discount does not fail a task loudly; it quietly forgives a real
    regression, which is the direction a benchmark must never err in.
    """
    import json as _json

    from tests.benchmark import runner as runner_mod

    instance = {"instance_id": "django__django-13551", "repo": "django/django",
                "FAIL_TO_PASS": ["t1"], "PASS_TO_PASS": ["t2"]}
    cache = tmp_path / "baselines"
    cache.mkdir()
    stale = {"instance_id": "django__django-13551",
             "pre_existing_failures": ["t2"] * 56,
             "target_already_passing": [], "measured_at": "2026-01-01T00:00:00"}
    (cache / "django__django-13551.json").write_text(_json.dumps(stale))

    measured = {}

    def fake_evaluate(container, inst, patch, timeout_s=900, known_failures=None,
                      on_event=None):
        measured["ran"] = True
        return {"regressions": [], "fail_to_pass_failing": []}

    monkeypatch.setattr(runner_mod, "evaluate", fake_evaluate)

    said = []
    result = runner_mod.baseline_failures(object(), instance, cache_dir=cache,
                                          on_event=said.append)

    # The stale entry is discarded, the baseline re-measured, and the reason
    # said out loud rather than swallowed.
    assert measured.get("ran") is True
    assert result["pre_existing_failures"] == []
    assert any("re-measuring" in text for text in said)

    # The fresh entry records its runner, so the NEXT read is a cache hit.
    measured.clear()
    again = runner_mod.baseline_failures(object(), instance, cache_dir=cache,
                                         on_event=said.append)
    assert measured.get("ran") is None
    assert again["runner"] == runner_mod._runner_signature(instance)
