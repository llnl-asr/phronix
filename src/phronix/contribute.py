"""Promote local learning up into the bundled layer, so everyone inherits it.

A lesson recorded while working on one project lands in that project's layer,
where it reaches the team that clones the repo. Some lessons deserve a wider
audience: a redaction rule for a token format, a skill about a widely-used tool,
a capability with no project-specific assumptions. Promotion is how those move
from one layer up to the one that ships inside the wheel.

It is deliberately a manual, reviewed step and never automatic. Two reasons:

* **Scope.** Most project learning is *correctly* project-scoped. Auto-promoting
  it would fill the shared bundle with facts that are wrong everywhere else, and
  a shared knowledge base that is often wrong is worse than a small one.
* **Privacy.** Promotion is publication. Every candidate goes through a privacy
  scan first, and anything with findings is refused rather than quietly redacted
  — silently rewriting text on its way out means nobody ever reviews what was in
  it.

Two modes, depending on where phronix itself is installed:

**Source checkout** (``pip install -e .`` from a clone) — the bundled layer is
writable and under version control, so candidates are copied in directly and you
commit and open a pull request as normal.

**Wheel install** — the bundled layer is inside ``site-packages``, where a write
would be lost on the next upgrade and invisible to git either way. Candidates are
exported to a directory instead, with instructions for opening the pull request
from a clone.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

#: What can be promoted. Memory is excluded on purpose: it is the most
#: project-specific tier by construction ("the state of OUR migration"), and a
#: memory that genuinely generalises should be rewritten as a skill lesson first.
#:
#: Verifiers ARE promotable, and promoting a skill without its verifier is the
#: mistake this list is arranged to make visible: it ships the claim and leaves
#: the evidence behind.
PROMOTABLE = ("skills", "agents", "capabilities", "verifiers")


def candidates(kinds: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Everything in the project/user layers that the bundled layer does not have.

    Reported as candidates, not as a diff: an entry that exists in both layers is
    an *override*, which is a deliberate local decision and not something to
    propose upstream.
    """
    from phronix.layers import bundled_layer, layers

    bundled = bundled_layer()
    wanted = [k for k in (kinds or PROMOTABLE) if k in PROMOTABLE]
    out: List[Dict[str, Any]] = []

    for layer in layers():
        if layer.name == "bundled":
            continue
        for kind in wanted:
            directory = layer.dir(kind)
            if not directory.is_dir():
                continue
            for entry in sorted(directory.iterdir()):
                if entry.name.startswith(".") or entry.name == "common-sections.yaml":
                    continue
                if kind == "skills" and not entry.is_dir():
                    continue
                if kind != "skills" and not entry.is_file():
                    continue
                target = bundled.dir(kind) / entry.name
                out.append({
                    "kind": kind,
                    "name": entry.stem if entry.is_file() else entry.name,
                    "source": str(entry),
                    "layer": layer.name,
                    "status": "overrides_bundled" if target.exists() else "new",
                })
    return out


def _scan(paths: List[Path]) -> List[Dict[str, Any]]:
    """Privacy findings across *paths*. Empty means safe to publish."""
    from phronix.privacy import current_users, find_identifiers

    users = current_users()
    findings: List[Dict[str, Any]] = []
    for path in paths:
        files = [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else [path]
        for file in files:
            try:
                text = file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            hits = find_identifiers(text, extra_users=users)
            if hits:
                findings.append({"file": str(file), "identifiers": sorted(set(hits))[:20]})
    return findings


#: How a candidate's ``kind`` maps to the verifier metadata ``kind``.
_VERIFIER_KIND = {"skills": "skill", "agents": "agent", "capabilities": "capability"}


def _verify_selection(selected: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run the verifiers attached to the selected candidates.

    Reports three groups, and the distinction between them is the whole point:

    * ``failed`` — a verifier ran and the claim did not hold. Blocking.
    * ``unverified`` — no verifier exists. Reported loudly but NOT blocking:
      refusing to promote anything without a verifier would simply stop people
      contributing, and a good lesson with no check is still better than no
      lesson. The report is what keeps the gap from being invisible.
    * ``passed`` — demonstrated, and safe to ship.
    """
    from phronix.verification import covers, run

    passed, failed, unverified = [], [], []
    for candidate in selected:
        kind = _VERIFIER_KIND.get(candidate["kind"])
        if kind is None:            # a verifier being promoted on its own
            continue
        names = covers(kind, candidate["name"])
        if not names:
            unverified.append({"kind": candidate["kind"], "name": candidate["name"]})
            continue
        outcome = run(kind=kind, target=candidate["name"])
        entry = {"kind": candidate["kind"], "name": candidate["name"],
                 "verifiers": names, "status": outcome["status"],
                 "summary": outcome["summary"]}
        # `fail` and `error` both block. A false claim must not ship, and neither
        # must an artifact whose corrector is broken — that is unverifiable content
        # wearing the appearance of coverage.
        #
        # `inconclusive` does NOT block: the check could not run HERE, which is not
        # evidence that the claim is wrong. Blocking on it would make promotion
        # impossible from any machine lacking the dependency.
        (failed if outcome["status"] in ("fail", "error") else passed).append(entry)
    return {"passed": passed, "failed": failed, "unverified": unverified}


def _attached_verifiers(selected: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The verifier files covering *selected*, as extra candidates to promote.

    Only verifiers that live outside the bundled layer are returned, and each at
    most once — a verifier already shipped, or already selected by name, must not
    be copied over itself.
    """
    from phronix.layers import bundled_layer, verifier_files
    from phronix.verification import covers

    bundled_root = str(bundled_layer().root)
    files = verifier_files()
    already = {c["source"] for c in selected}
    extra: List[Dict[str, Any]] = []

    for candidate in selected:
        kind = _VERIFIER_KIND.get(candidate["kind"])
        if kind is None:
            continue
        for name in covers(kind, candidate["name"]):
            path = files.get(f"{name}.py")
            if path is None or str(path).startswith(bundled_root) or str(path) in already:
                continue
            already.add(str(path))
            extra.append({
                "kind": "verifiers", "name": name, "source": str(path),
                "layer": candidate["layer"], "status": "new",
                "attached_to": f"{candidate['kind']}:{candidate['name']}",
            })
    return extra


def promote(
    names: Optional[List[str]] = None,
    kinds: Optional[List[str]] = None,
    output: Optional[Path] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Copy candidates into the bundled layer, or export them for a pull request.

    Args:
        names: restrict to these skill/agent/capability names. Default: all
            candidates whose status is ``new``.
        kinds: restrict to some of :data:`PROMOTABLE`.
        output: export here instead of writing to the bundled layer. Implied when
            the bundled layer is not writable.
        force: promote despite privacy findings. Requires a deliberate choice,
            because promotion is publication and a leak here is permanent.

    Returns a dict with ``status``, ``promoted``, ``skipped``, ``findings`` and
    ``next`` — the instruction for what the caller has to do to finish.
    """
    from phronix.layers import bundled_layer

    everything = candidates(kinds)
    selected = [c for c in everything if c["status"] == "new"]
    if names:
        wanted = {n.strip().lower() for n in names}
        selected = [c for c in everything if c["name"].lower() in wanted]
    if not selected:
        return {"status": "nothing_to_promote", "candidates": everything,
                "next": "Nothing in the project or user layers is missing from the "
                        "bundled layer. Pass explicit names to promote an override."}

    findings = _scan([Path(c["source"]) for c in selected])
    if findings and not force:
        return {
            "status": "blocked_by_privacy",
            "findings": findings,
            "selected": selected,
            "next": "Promotion is publication. Fix these with privacy_redact (or "
                    "`phronix privacy redact`), then run this again. Use force=True "
                    "only if you have reviewed each finding and it is not identifying.",
        }

    verification = _verify_selection(selected)
    if verification["failed"] and not force:
        return {
            "status": "blocked_by_verification",
            "verification": verification,
            "selected": selected,
            "next": "These artifacts have verifiers, and the verifiers do not pass. "
                    "Promoting them would ship a claim that is demonstrably false to "
                    "everyone who installs phronix. Fix the lesson or the code, then "
                    "run this again.",
        }

    bundled = bundled_layer()
    destination_root = Path(output) if output else (bundled.root if bundled.writable else None)
    if destination_root is None:
        return {
            "status": "needs_output_dir",
            "selected": selected,
            "next": "phronix is installed as a wheel, so the bundled layer is inside "
                    "site-packages: writing there would be lost on upgrade and is "
                    "invisible to git. Re-run with an output directory, then open a "
                    "pull request from a clone of phronix:\n"
                    "  phronix contribute --output /tmp/phronix-contribution\n"
                    "  git clone https://github.com/hariharan-devarajan/phronix\n"
                    "  cp -r /tmp/phronix-contribution/* phronix/src/phronix/.phronix/",
        }

    # Evidence travels with the claim. Promoting a skill and leaving its verifier
    # behind ships an assertion nobody downstream can re-check — the precise
    # failure the verification tier exists to prevent, so it is not left to the
    # caller to remember.
    selected = selected + _attached_verifiers(selected)

    promoted: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []
    for candidate in selected:
        source = Path(candidate["source"])
        destination = destination_root / candidate["kind"] / source.name
        if destination.exists() and not force:
            skipped.append({**candidate, "reason": "already exists at destination"})
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            if source.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
        except OSError as exc:
            skipped.append({**candidate, "reason": str(exc)})
            continue
        promoted.append({**candidate, "destination": str(destination)})

    exported = output is not None or not bundled.writable
    return {
        "status": "ok" if promoted else "nothing_promoted",
        "promoted": promoted,
        "skipped": skipped,
        "findings": findings,
        "verification": verification,
        "destination": str(destination_root),
        "next": (
            f"Exported to {destination_root}. Copy it into a phronix clone under "
            "src/phronix/.phronix/ and open a pull request."
            if exported else
            "Written into the bundled layer. Review with `git diff`, then commit and "
            "open a pull request — this is what ships to every phronix installer."
        ),
    }


def main() -> None:
    """Entry point for ``phronix-contribute``."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        prog="phronix-contribute",
        description="Promote skills, agents or capabilities from this project up "
                    "into the bundled layer, so every phronix installer inherits them.",
    )
    parser.add_argument("names", nargs="*",
                        help="Specific names to promote (default: everything the "
                             "bundled layer does not already have).")
    parser.add_argument("--kind", action="append", choices=PROMOTABLE, default=None)
    parser.add_argument("--output", default=None,
                        help="Export here instead of writing to the bundled layer.")
    parser.add_argument("--list", action="store_true", help="Show candidates and exit.")
    parser.add_argument("--force", action="store_true",
                        help="Proceed despite privacy findings or an existing destination.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list:
        found = candidates(args.kind)
        if args.json:
            print(json.dumps(found, indent=2))
            return
        if not found:
            print("No promotable content in the project or user layers.")
            return
        for entry in found:
            print(f"  {entry['status']:18s} {entry['layer']:8s} {entry['kind']:13s} {entry['name']}")
        return

    result = promote(args.names or None, args.kind,
                     Path(args.output) if args.output else None, args.force)
    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"Status: {result['status']}")
    for entry in result.get("promoted", []):
        print(f"  + {entry['kind']:13s} {entry['name']}")
    for entry in result.get("skipped", []):
        print(f"  ! {entry['kind']:13s} {entry['name']}  ({entry['reason']})")
    for finding in result.get("findings", []):
        print(f"  PRIVACY {finding['file']}: {', '.join(finding['identifiers'][:5])}")
    print(f"\n{result['next']}")


if __name__ == "__main__":
    main()
