"""Verification tools: prove that what was learned is still true.

Four tools rather than one per verifier. Registering an MCP tool per verifier
would put every check's schema in the model's context on every turn, for the
whole session, growing without bound as the knowledge base does — the same
reasoning that keeps the graph to three wrappers instead of graphify's twenty-five
schemas. ``verify_run`` dispatches by target, which gives the same reach at a
fixed cost.
"""
from __future__ import annotations

import json
from typing import Any


def register(mcp: Any) -> None:
    @mcp.tool()
    def verify_list() -> str:
        """List every verifier: what it checks, the claim it makes, and its layer.

        A verifier is the executable check paired with a piece of learning. Call
        this to see what the project can actually prove about itself, as opposed to
        what it merely asserts in prose.

        An entry with an ``error`` field failed to import — that is a broken check,
        which is worse than a missing one, because the directory listing still
        makes it look like coverage.

        Returns JSON: {status, count, verifiers: [{name, kind, target, claim,
        layer, callable}]}.
        """
        from phronix.verification import discover

        verifiers = discover()
        return json.dumps({
            "status": "ok",
            "count": len(verifiers),
            "verifiers": verifiers,
            "usage": "verify_run(target=...) to execute; verify_coverage() to find "
                     "learning with no check behind it.",
        }, indent=2)

    @mcp.tool()
    def verify_run(name: str = "", kind: str = "", target: str = "",
                   include_builtin: bool = True) -> str:
        """Run the correctors and report whether what was learned still holds.

        **Run this after recording anything, after any self-heal, and before
        reporting work as done.** Learning and healing are predictions; this is the
        deterministic check that anchors them. A lesson nobody can re-check is an
        assertion, not knowledge — and one that was true when written rots silently
        as the world moves.

        Two layers run together:

        - **Built-in structural correctors**, automatic for every skill,
          capability and agent: frontmatter parses, names match, includes resolve,
          modules compile and register documented tools, templates render for all
          four harnesses, nothing identifies a person.
        - **Authored spec verifiers**, which check the claim about the world that
          structure cannot settle. Each evaluates five facets — assumptions,
          inputs, constraints, invariants, outputs — and reports them separately,
          so a failure names WHICH part of the claim broke.

        Four outcomes, and the distinctions carry the signal:

        - ``pass`` — every facet held.
        - ``fail`` — a constraint, invariant or output did not hold. Something
          recorded as true is now false: fix the lesson, or fix the world.
        - ``inconclusive`` — an assumption or required input did not resolve, so
          the check could not run here. Not evidence either way, and NOT a failure.
        - ``error`` — the verifier itself raised, or its spec is malformed. A bug
          in the check, reported separately so broken correctors cannot hide inside
          genuine failures.

        Args:
            name: run one verifier by module name.
            kind: skill | capability | agent | memory.
            target: the artifact whose correctors should run.
            include_builtin: also run the built-in structural correctors. Leave
                this on for any completeness check — they are the only layer with
                total coverage.

        Returns JSON: {status, counts, summary, results: [{name, source, kind,
        target, claim, status, evidence, facets}]}. Read ``facets`` on a failure:
        it says exactly which assumption, constraint, invariant or output broke.
        """
        from phronix.verification import run

        try:
            return json.dumps(
                run(name=name, kind=kind, target=target, include_builtin=include_builtin),
                indent=2)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})

    @mcp.tool()
    def verify_coverage() -> str:
        """Report which learning has a verifier behind it — and which does not.

        **This is the number that matters for trust.** A knowledge base with a
        hundred lessons and six verifiers holds ninety-four unverified claims
        wearing the appearance of authority, and that gap is invisible unless
        something reports it.

        Call this before finishing a session. Every artifact you created or
        changed should appear in ``covered_detail``; anything of yours in
        ``uncovered_detail`` is learning you have asserted but cannot demonstrate.

        Also reports:

        - ``orphaned_verifiers`` — checks whose target no longer exists. Dead
          weight that still looks like coverage to anyone skimming.
        - ``never_run`` — verifiers that have never executed on this machine. A
          verifier that has never run is not evidence; it is an untested claim
          about an untested claim.

        Memory is excluded by design: a memory records a decision or a piece of
        state, not something code can falsify.

        Returns JSON: {status, total_artifacts, covered, uncovered, percent,
        covered_detail, uncovered_detail, orphaned_verifiers, never_run}.
        """
        from phronix.verification import coverage

        try:
            return json.dumps(coverage(), indent=2)
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})

    @mcp.tool()
    def verify_new(
        name: str,
        kind: str,
        target: str,
        claim: str,
        source: str = "",
        layer: str = "",
        overwrite: bool = False,
    ) -> str:
        """Write the deterministic corrector that anchors a piece of learning.

        **Pair this with every `skill_write`, `capability_new`, and agent change.**
        Learning and healing are predictors — they propose what is true and what
        fixes it. This is the corrector: a fixed algorithm, no model in the loop,
        that says whether the prediction holds. Without one, a wrong lesson is
        indistinguishable from a right one and will be trusted long after it stops
        being true.

        A verifier is a structured SPEC with five facets, each checked and reported
        separately — "it failed" is not actionable and "it passed" is not
        trustworthy::

            SPEC = {
                "kind": "skill",
                "target": "software-postgres",
                "claim": "pg_restore accepts --jobs, spelled as the lesson says.",

                "assumptions": [                       # preconditions
                    {"name": "installed", "detail": "pg_restore on PATH",
                     "check": lambda ctx: shutil.which("pg_restore") is not None}],

                "inputs": [                            # what it operates on
                    {"name": "help_text", "required": True,
                     "resolve": lambda ctx: subprocess.run(
                         ["pg_restore", "--help"], capture_output=True,
                         text=True).stdout}],

                "constraints": [                       # what the claim asserts
                    {"name": "flag_spelled_jobs", "detail": "the lesson's spelling",
                     "check": lambda ctx: ("--jobs" in ctx["help_text"],
                                           ctx["help_text"][:200])}],

                "invariants": [                        # must not change
                    {"name": "no_db_writes",
                     "sample": lambda ctx: Path("/tmp/pgdata").stat().st_mtime}],

                "outputs": [                           # what must be produced
                    {"name": "help_non_empty",
                     "check": lambda ctx: len(ctx["help_text"]) > 100}],
            }

        **The facets have different meanings, and that is the point:**

        - `assumptions` and `inputs` GATE the run. If a precondition does not hold
          or a required input will not resolve, the result is `inconclusive` — the
          check could not run here, which is not evidence that the claim is wrong.
        - `constraints` are the claim itself. These are what `fail` means.
        - `invariants` are sampled before AND after and compared. A change means
          verifying the thing altered it, which invalidates the whole run.
        - `outputs` are what must have been produced, and their shape.

        **Keep every check deterministic.** Same inputs, same verdict, every run,
        on every machine. No model calls, no wall-clock branching, no network
        unless the claim is about the network. A non-deterministic corrector is not
        an anchor.

        **Write a falsifiable claim.** "The flag is spelled --jobs" can be wrong.
        "Postgres works" cannot, so a verifier for it proves nothing.

        **Return real evidence** — the command output, the file contents, the value
        read. Each check may return a bool, `(ok, evidence)`, or
        `{"ok": ..., "evidence": ...}`.

        Note that every skill, capability and agent ALREADY has a built-in
        structural corrector (frontmatter, includes, compilation, tool docstrings,
        renderability, privacy). This tool adds the layer that structure cannot
        settle: whether the claim about the world is true.

        Args:
            name: snake_case module name.
            kind: skill | capability | agent | memory.
            target: the artifact this corrects.
            claim: the specific, falsifiable statement being checked.
            source: full module text. Omit for a scaffold — but a scaffold has no
                constraints and therefore cannot fail, so finish it.
            layer: force a target layer; defaults to the learning's own audience.
            overwrite: replace an existing verifier of the same name.

        Returns JSON: {status, file, layer, verifies, facets, next}. Run
        `verify_run(name=...)` afterwards — a verifier that has never executed is
        not evidence.
        """
        from phronix.verification import new

        try:
            return json.dumps(
                new(name, kind, target, claim, source=source or None,
                    layer=layer or None, overwrite=overwrite),
                indent=2,
            )
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
