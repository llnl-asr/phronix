"""Anonymization for everything phronix persists or publishes.

Skills, agent templates, memory and learned capabilities are all designed to
travel — into a git repo, into a wheel, into someone else's clone. The point of
the framework is to learn from experience without recording *whose* experience
it was, so any text on its way into one of those passes through
:func:`anonymize` first.

The substitutions are deliberately conservative. They replace identity and
machine-local location with shell variables a reader can resolve for themselves
(``$USER``, ``$HOME``, ``$PROJECT_ROOT``), and collapse run-specific identifiers
(job ids, session UUIDs, node hostnames) into angle-bracket placeholders. What
survives is the lesson; what is dropped is the provenance.

Two escape hatches exist because blanket redaction is wrong in specific places:

* **Citations pass through untouched.** A paper's author list is a public
  reference, not telemetry, and mangling it breaks the citation.
* **Structured formats keep their shape.** For a ``.patch``/``.diff``,
  collapsing ``/home/alice/proj/x`` to ``$HOME/proj/x`` changes the leading
  component count and silently breaks ``patch -pN``. :data:`_IDENTITY_ONLY`
  replaces only the username segment, preserving both component and line counts.

Rules the guard *learns* (corner cases these built-ins miss) are data, not code:
they live in each layer's ``privacy_patterns.yaml`` so a new rule can be
persisted by a tool call and ship to everyone, without editing this module.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

#: Lines matching these are bibliography, not telemetry — never rewritten.
_CITATION_LINE: Pattern[str] = re.compile(
    r"\*\*Citation:\*\*|\*\*Authors:\*\*|^\s*\[\d+\]\s", re.IGNORECASE
)

#: A path segment that is ALREADY anonymous. ``/home/$USER`` is the desired
#: output, not a leak, so the location patterns below must not re-match it and
#: produce ``/home/$USER$USER``.
_PLACEHOLDER = r"(?!\$|<|\*|\.\.\.)"

#: A trailing path segment: anything up to a separator, whitespace, or a quote.
_SEG = r"[^/\s\"')`]+"

#: Scheduler job ids of the base58 family (Flux and friends): an ``f`` followed by
#: a long mixed-case alphanumeric run.
#:
#: The two lookaheads are what make this safe. Requiring BOTH a digit and an
#: uppercase letter separates ``fA1b2C3d4E5f6`` from ordinary long words starting
#: with f — ``functionality`` is 13 characters and would otherwise match, silently
#: corrupting prose.
_JOB_ID: Pattern[str] = re.compile(
    r"\bf(?=[A-Za-z0-9]*[0-9])(?=[A-Za-z0-9]*[A-Z])[A-Za-z0-9]{10,}\b")

_UUID: Pattern[str] = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")

#: Hostnames like ``nodename1002`` -> ``nodename<node>``: keep the cluster name,
#: drop which machine.
#:
#: Narrow on purpose. A bare ``[a-z]{4,}\d{3,4}`` also eats build and wheel tags
#: such as ``rocm710`` in ``torch==2.10.0+rocm710``. So: reject anything glued to a
#: version string by a preceding ``+ = . - _`` or word character, and reject the
#: software prefixes that legitimately carry digits.
_HOSTNAME: Pattern[str] = re.compile(
    r"(?<![+=.\-_\w])"
    r"(?!(?:rocm|cuda|hip|gcc|cce|craype|python|torch|node|rhel|toss|glibc|ubuntu)\d)"
    r"([a-z]{4,})\d{3,4}\b")

#: An email address, excluding SSH/git remotes (``git@github.com``) and ELF symbol
#: version tags (``_ZSt@GLIBCXX_3.4.26``) — neither of which is a person.
_EMAIL: Pattern[str] = re.compile(
    r"(?<![\w.@])(?!git@)[\w.+-]+@(?![A-Z_])[a-z0-9-]+\.[a-z]{2,}\b")

_SESSION_ID: Pattern[str] = re.compile(r"\borigin_?[Ss]ession_?[Ii]d:.*$", re.MULTILINE)

#: Ordered longest/most-specific first, so a path is rewritten as a path before
#: its embedded username is rewritten as ``$USER``.
_SUBS: List[Tuple[Pattern[str], str]] = [
    # Absolute, user-rooted filesystem locations. Each requires a concrete
    # (non-placeholder) segment where the username sits. HPC site layouts are
    # included because that is where this framework is used most, and a
    # `/p/lustre2/<user>` leak is exactly as identifying as a `/home/<user>` one.
    (re.compile(rf"/p/lustre\d*/{_PLACEHOLDER}{_SEG}"), "$SCRATCH_ROOT"),
    (re.compile(rf"/p/vast\d*/{_PLACEHOLDER}{_SEG}"), "$SCRATCH_ROOT"),
    (re.compile(rf"/g/g\d+/{_PLACEHOLDER}{_SEG}"), "$HOME"),
    (re.compile(rf"/usr/(?:WS|workspace)\d*/{_PLACEHOLDER}{_SEG}"), "$HOME"),
    (re.compile(rf"/(?:home|Users)/{_PLACEHOLDER}{_SEG}"), "$HOME"),
    # Identity, then run- and machine-specific identifiers.
    (_EMAIL, "<redacted-email>"),
    (_SESSION_ID, ""),
    (_JOB_ID, "<job-id>"),
    (_UUID, "<uuid>"),
    (_HOSTNAME, r"\1<node>"),
]

#: Substitutions that remove identity WITHOUT changing a path's shape — used for
#: unified diffs and any other format whose parser counts path components or
#: lines. Replacing only the username keeps both counts identical, so the patch
#: stays structurally valid.
_IDENTITY_ONLY: List[Tuple[Pattern[str], str]] = [
    (_EMAIL, "<redacted-email>"),
    (_SESSION_ID, ""),
    (_JOB_ID, "<job-id>"),
    (_UUID, "<uuid>"),
    # Replace ONLY the username segment, keeping the component count. This also
    # catches OTHER people's usernames, which `extra_users` cannot know about.
    (re.compile(rf"(/(?:home|Users)/){_PLACEHOLDER}{_SEG}"), r"\1$USER"),
    (re.compile(rf"(/usr/(?:WS|workspace)\d*/){_PLACEHOLDER}{_SEG}"), r"\1$USER"),
    (re.compile(rf"(/p/lustre\d*/){_PLACEHOLDER}{_SEG}"), r"\1$USER"),
    (re.compile(rf"(/p/vast\d*/){_PLACEHOLDER}{_SEG}"), r"\1$USER"),
    (re.compile(rf"(/g/g\d+/){_PLACEHOLDER}{_SEG}"), r"\1$USER"),
    (_HOSTNAME, r"\1<node>"),
]

#: Formats whose structure must survive redaction.
STRUCTURED_SUFFIXES = frozenset({".patch", ".diff"})

#: Opt-out marker for files whose CONTENT is deliberately identifying-looking.
#:
#: Exactly one legitimate case: a file whose job is to test the redactor must
#: contain the inputs it redacts. Without an exemption the sweep is permanently
#: non-clean, and a check that is always yellow is a check people stop reading —
#: which costs more than the fixtures ever could.
#:
#: Deliberately narrow and visible: the marker must state a reason on the same
#: line, exemptions are reported in the scan output rather than silently skipped,
#: and this cannot be applied to a whole directory.
EXEMPT_MARKER = "phronix: privacy-fixture"


def exemption_reason(text: str) -> Optional[str]:
    """The stated reason a file is exempt from the privacy sweep, or ``None``.

    A marker with no reason does not exempt: the whole point is that somebody can
    later judge whether the exemption is still warranted.
    """
    for line in text.split("\n")[:40]:  # header only — not buried mid-file
        if EXEMPT_MARKER in line:
            reason = line.split(EXEMPT_MARKER, 1)[1].strip(" -—:#\t")
            return reason or None
    return None


# ---------------------------------------------------------------------------
# Learned rules — data, so the guard can grow without a code change
# ---------------------------------------------------------------------------

def patterns_files() -> List[Path]:
    """Every layer's ``privacy_patterns.yaml``, lowest precedence first."""
    from phronix.layers import layers

    return [p for p in ((layer.root / "privacy_patterns.yaml") for layer in layers())
            if p.is_file()]


def learned_patterns() -> List[Dict[str, object]]:
    """Corner-case rules the privacy guard discovered in past sessions.

    Merged across layers so a project can add a redaction rule for its own
    internal hostnames without having to ship it upstream first. A malformed
    file is skipped rather than raising: a broken learned rule must never take
    down the redactor and let unredacted text through by exception.
    """
    out: List[Dict[str, object]] = []
    for path in patterns_files():
        try:
            import yaml

            data = yaml.safe_load(path.read_text()) or {}
            for entry in data.get("patterns") or []:
                if isinstance(entry, dict):
                    out.append(entry)
        except Exception:
            continue
    return out


def _compiled_learned(preserve_structure: bool) -> List[Tuple[Pattern[str], str]]:
    """Compile the learned rules, skipping path-reshaping ones for diffs."""
    out: List[Tuple[Pattern[str], str]] = []
    for entry in learned_patterns():
        if preserve_structure and not entry.get("structure_safe", True):
            continue
        try:
            out.append((re.compile(str(entry["regex"])), str(entry["replacement"])))
        except (KeyError, re.error):
            continue
    return out


def add_pattern(
    regex: str,
    replacement: str,
    reason: str,
    structure_safe: bool = True,
    layer: Optional[str] = None,
) -> Dict[str, object]:
    """Persist a new redaction rule to a layer's ``privacy_patterns.yaml``.

    The regex is compiled before it is written: a rule that cannot compile is
    a rule that silently does nothing, and finding that out at redaction time
    means the leak already happened.
    """
    import yaml

    from phronix.layers import resolve_write_layer

    re.compile(regex)  # fail loudly here, not silently at redaction time

    target = resolve_write_layer(layer)
    path = target.root / "privacy_patterns.yaml"
    data = {}
    if path.is_file():
        data = yaml.safe_load(path.read_text()) or {}
    entries = list(data.get("patterns") or [])
    if any(e.get("regex") == regex for e in entries if isinstance(e, dict)):
        return {"status": "already_present", "file": str(path), "regex": regex}

    entries.append({
        "regex": regex,
        "replacement": replacement,
        "reason": reason,
        "structure_safe": bool(structure_safe),
    })
    data["patterns"] = entries
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return {"status": "added", "file": str(path), "layer": target.name, "regex": regex}


# ---------------------------------------------------------------------------
# Suspect probes — finding the corner cases the rules do not cover yet
# ---------------------------------------------------------------------------
#
# These never rewrite anything. They exist so the guard can DISCOVER a leak
# class instead of waiting to be told about one: whatever `anonymize` already
# handles is filtered out, so what a probe still matches is precisely a rule we
# do not have yet.

#: Directories that are identical on every machine — a path through one of them
#: names software, not a person.
_SYSTEM_DIRS = (
    "local|tce|gapps|global|share|lib|lib64|bin|sbin|include|opt|src|apps|"
    "workspace|WS|projects|tmp|var|etc"
)

_SUSPECT_PROBES: List[Tuple[str, Pattern[str]]] = [
    (
        "home-like path",
        re.compile(rf"/(?:home|users|Users|nfs|work|scratch)/(?!(?:{_SYSTEM_DIRS})/)[A-Za-z][\w.-]{{2,}}"),
    ),
    # Neither the site segment nor the one after it may be a system dir:
    # `/usr/local/lib` and `/usr/share/doc` name software, not people.
    (
        "site path with user segment",
        re.compile(
            rf"/(?:p|g|usr)/(?!(?:{_SYSTEM_DIRS})/)[\w.]+/"
            rf"(?!(?:{_SYSTEM_DIRS}|packages|tools|python)/)[A-Za-z][\w.-]{{2,}}/"
        ),
    ),
    # `(?<![+\w.@])` also rejects the `+@decorator` lines inside unified diffs.
    (
        "possible email",
        re.compile(r"(?<![+\w.@])(?!git@)[\w.+-]+@(?![A-Z_])[a-z0-9-]+\.[a-z]{2,}\b"),
    ),
    ("ssh url", re.compile(r"(?<![\w.])(?!git@)[\w.-]+@[\w.-]+:[\w./-]+")),
    # An opaque id must actually look opaque: mixed alnum WITH digits, so a
    # camelCase config key like `checkpointFileIntervalTime` does not qualify.
    ("long opaque id", re.compile(r"\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[a-zA-Z])[a-f0-9]{16,}\b")),
    # Mirror the real hostname rule's shape so the probe agrees with the redactor.
    ("hostname-like", re.compile(r"(?<![+=.\-_\w])[a-z]{4,}\d{3,4}\b")),
    # Only flag an IP in a network context, and never loopback/private ranges —
    # otherwise every `HDF5 1.14.3.3` version string looks like an address.
    (
        "ip address",
        re.compile(
            r"(?:https?://|@|host[=: ]|addr[=: ])"
            r"(?!127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)"
            r"(?:\d{1,3}\.){3}\d{1,3}"
        ),
    ),
    ("api key-ish", re.compile(r"\b(?:sk|ghp|gho|pat|xox[baprs])[-_][A-Za-z0-9]{8,}\b")),
    ("aws key-ish", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("uid/gid", re.compile(r"\b(?:uid|gid)=(?!0\b)\d{3,}")),  # uid=0 is root, not a person
]


def suspects(text: str, extra_users: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """Return ``(probe_name, matched_text)`` for content that *may* identify.

    A match here is a candidate, not a confirmed leak. Anything :func:`anonymize`
    already rewrites is subtracted first, so what remains is the corner cases the
    current rules miss. The guard reviews these and, when one is real, persists a
    rule with :func:`add_pattern`.
    """
    found: List[Tuple[str, str]] = []
    for line in text.split("\n"):
        if _CITATION_LINE.search(line):
            continue
        residue = anonymize(line, extra_users=extra_users)
        for name, probe in _SUSPECT_PROBES:
            for match in probe.finditer(residue):
                token = match.group(0)
                if any(ph in token for ph in ("$", "<", "*", "...")):
                    continue
                found.append((name, token))
    return found


# ---------------------------------------------------------------------------
# The redactor
# ---------------------------------------------------------------------------

def anonymize(
    text: str,
    extra_users: Optional[List[str]] = None,
    preserve_structure: bool = False,
) -> str:
    """Return *text* with identity and machine-local detail removed.

    Args:
        text: the content on its way into a persisted or published artifact.
        extra_users: additional bare usernames to replace with ``$USER`` — pass
            the current user, whose name cannot be inferred when it appears
            outside a path.
        preserve_structure: use for ``.patch``/``.diff``. Absolute paths keep
            their shape and only the username inside them is replaced, so hunk
            offsets and ``-pN`` strip counts survive.
    """
    subs = list(_IDENTITY_ONLY if preserve_structure else _SUBS)
    subs.extend(_compiled_learned(preserve_structure))
    for user in extra_users or []:
        if user:
            subs.append((re.compile(rf"\b{re.escape(user)}\b"), "$USER"))

    out = []
    for line in text.split("\n"):
        if _CITATION_LINE.search(line):
            out.append(line)
            continue
        for pattern, repl in subs:
            line = pattern.sub(repl, line)
        out.append(line)
    return "\n".join(out)


def anonymize_path(path: Path, extra_users: Optional[List[str]] = None) -> str:
    """Redact a file's text, picking structure preservation from its suffix."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return anonymize(
        text,
        extra_users=extra_users,
        preserve_structure=Path(path).suffix in STRUCTURED_SUFFIXES,
    )


def find_identifiers(text: str, extra_users: Optional[List[str]] = None) -> List[str]:
    """Return the identifying substrings :func:`anonymize` would rewrite.

    Lets a caller assert that a file is clean, or report what it changed, without
    diffing the whole document.
    """
    hits: List[str] = []
    subs = list(_SUBS)
    subs.extend(_compiled_learned(preserve_structure=False))
    for user in extra_users or []:
        if user:
            subs.append((re.compile(rf"\b{re.escape(user)}\b"), "$USER"))
    for line in text.split("\n"):
        if _CITATION_LINE.search(line):
            continue
        for pattern, _ in subs:
            hits.extend(m.group(0) for m in pattern.finditer(line))
    return hits


def current_users() -> List[str]:
    """The bare usernames worth redacting on this machine."""
    import getpass
    import os

    names = set()
    try:
        names.add(getpass.getuser())
    except Exception:
        pass
    for key in ("USER", "LOGNAME", "USERNAME"):
        value = os.environ.get(key)
        if value:
            names.add(value)
    return sorted(n for n in names if n and n != "root")
