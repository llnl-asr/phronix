"""Verifies: the redaction behaviour the phronix-privacy skill documents is real.

phronix: privacy-fixture — this file must contain the identifying-looking inputs
it feeds to the redactor; they are synthetic fixtures, not anyone's real data.

The skill tells agents what will and will not be stripped, and agents act on that
without re-deriving it. If the redactor's behaviour and the skill's description
ever diverge, every session is working from a false model of what is safe to
write — and the divergence is silent, because nothing reads the skill and the code
together.

This is the corrector for that claim. Entirely deterministic: pure string
substitution over fixed inputs, no environment, no network, no clock.
"""
from __future__ import annotations

from phronix.privacy import anonymize, suspects

#: Cases the skill promises WILL be redacted, as (input, expected output).
_MUST_REDACT = [
    ("/home/exampleuser/proj/x.py", "$HOME/proj/x.py"),
    ("/usr/workspace/exampleuser/thing", "$HOME/thing"),
    ("run 550e8400-e29b-41d4-a716-446655440000", "run <uuid>"),
    ("built on examplehost1002", "built on examplehost<node>"),
]

#: Cases the skill promises will NOT be touched. Over-redaction is a real failure:
#: it makes knowledge unusable and trains people to disable the guard, which is
#: how the actual leaks get through.
_MUST_PRESERVE = [
    "**Authors:** A Researcher, B Researcher (someone@example.com)",  # citation
    "torch==2.10.0+rocm710",                                          # version tag
    "git@github.com:org/repo.git",                                    # SSH remote
    "$HOME/proj",                                                     # already anonymous
    "/home/$USER/proj",                                               # already anonymous
]


def _redacts_everything(ctx):
    wrong = [f"{src!r} -> {anonymize(src)!r}, expected {want!r}"
             for src, want in _MUST_REDACT if anonymize(src) != want]
    return (not wrong, "; ".join(wrong) if wrong else
            f"all {len(_MUST_REDACT)} documented redactions behave as described")


def _preserves_everything(ctx):
    wrong = [f"{src!r} -> {anonymize(src)!r}" for src in _MUST_PRESERVE
             if anonymize(src) != src]
    return (not wrong, "; ".join(wrong) if wrong else
            f"all {len(_MUST_PRESERVE)} exempt cases pass through untouched")


def _structure_is_preserved(ctx):
    """A diff must keep its component count, or `patch -pN` breaks."""
    line = "--- a/home/exampleuser/proj/x.py"
    out = anonymize(line, preserve_structure=True)
    ok = out.count("/") == line.count("/") and "exampleuser" not in out
    return ok, f"{line!r} -> {out!r}"


def _idempotent(ctx):
    """Redacting twice must equal redacting once, or repeated writes corrupt text."""
    wrong = [src for src, _ in _MUST_REDACT
             if anonymize(anonymize(src)) != anonymize(src)]
    return (not wrong, f"not idempotent for: {wrong}" if wrong else
            "redaction is idempotent over every documented case")


def _suspects_excludes_handled(ctx):
    """A path the redactor already rewrites must not also be reported as a suspect.

    If it were, the suspect list would fill with things that are already handled
    and the genuine corner cases would be invisible in the noise.
    """
    probes = {name for name, _ in suspects("/home/exampleuser/proj")}
    return ("home-like path" not in probes,
            f"probes fired on already-handled input: {sorted(probes)}")


def _line_count_unchanged(ctx):
    text = "\n".join(["/home/exampleuser/a", "safe line", "/home/otheruser/b"])
    out = anonymize(text)
    return out.count("\n") == text.count("\n"), f"{text.count(chr(10))} -> {out.count(chr(10))}"


SPEC = {
    "kind": "skill",
    "target": "phronix-privacy",
    "claim": (
        "The redactor strips exactly what the phronix-privacy skill says it strips "
        "(home paths, UUIDs, hostnames), preserves exactly what the skill says is "
        "exempt (citations, version tags, SSH remotes, existing placeholders), and "
        "preserves path and line structure for diffs."
    ),

    # No environment preconditions: this is pure string work, so it can run
    # anywhere. An empty assumptions list is the correct answer here, not an
    # oversight — inventing one would make the check weaker, not stronger.
    "assumptions": [],

    "inputs": [
        {"name": "cases",
         "detail": "the documented redact/preserve cases, defined in this module",
         "required": True,
         "resolve": lambda ctx: {"redact": _MUST_REDACT, "preserve": _MUST_PRESERVE}},
    ],

    "constraints": [
        {"name": "documented_redactions_hold",
         "detail": "everything the skill says is stripped, is stripped",
         "check": _redacts_everything},
        {"name": "documented_exemptions_hold",
         "detail": "everything the skill says is exempt, survives untouched",
         "check": _preserves_everything},
        {"name": "diff_structure_preserved",
         "detail": "preserve_structure keeps the path component count",
         "check": _structure_is_preserved},
        {"name": "redaction_is_idempotent",
         "detail": "redacting an already-redacted string is a no-op",
         "check": _idempotent},
        {"name": "suspects_excludes_handled_cases",
         "detail": "suspect probes do not re-report what the rules already fix",
         "check": _suspects_excludes_handled},
    ],

    "invariants": [
        # The rule set itself must not change as a side effect of running the
        # checks. A corrector that mutates the thing it verifies invalidates its
        # own result, and learned rules are loaded from disk on every call.
        {"name": "rule_count_stable",
         "detail": "running the checks does not add or drop redaction rules",
         "sample": lambda ctx: (len(__import__("phronix.privacy", fromlist=["_SUBS"])._SUBS),
                                len(__import__("phronix.privacy",
                                               fromlist=["_IDENTITY_ONLY"])._IDENTITY_ONLY))},
    ],

    "outputs": [
        {"name": "line_count_unchanged",
         "detail": "redaction never adds or removes lines",
         "check": _line_count_unchanged},
    ],
}
