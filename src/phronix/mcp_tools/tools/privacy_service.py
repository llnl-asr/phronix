"""Privacy tools: verify deterministically that nothing shared identifies anyone.

Everything phronix persists is committed and travels. Reading a file and judging
it "looks fine" does not scale and does not catch the classes of leak a regex
does — so these tools make the check mechanical, and make *finding a new leak
class* a first-class operation rather than something that only happens after an
incident.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional


def _targets(paths: Optional[List[str]]) -> List[Path]:
    """Resolve a path list to files, defaulting to the whole layered store."""
    if not paths:
        from phronix.layers import iter_all_content

        return list(iter_all_content())
    out: List[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            out.extend(p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            out.append(path)
    return out


def register(mcp: Any) -> None:
    @mcp.tool()
    def privacy_scan(paths: Optional[List[str]] = None) -> str:
        """Check that shared content carries no identifying detail. Changes nothing.

        Run this before finishing a session that wrote skills, memories or
        capabilities, and before opening any pull request. Reports every file that
        would change under redaction, and exactly which substrings would change.

        Args:
            paths: files or directories to check. Defaults to the entire layered
                store — every skill, agent template, memory and capability.

        A file may opt out with a ``phronix: privacy-fixture`` marker AND a stated
        reason — the one legitimate case is a corrector whose job is to test the
        redactor, which must contain the inputs it redacts. Exemptions are
        REPORTED, not silently skipped, so they stay reviewable.

        Returns JSON: {status, checked, clean, findings: [{file, identifiers}],
        exempt: [{file, reason}]}. ``status`` is "clean" or "findings". Treat
        anything but "clean" as blocking: fix it with ``privacy_redact``.
        """
        from phronix.privacy import current_users, exemption_reason, find_identifiers

        users = current_users()
        findings, exempt = [], []
        checked = 0
        for path in _targets(paths):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            checked += 1
            hits = find_identifiers(text, extra_users=users)
            if not hits:
                continue
            reason = exemption_reason(text)
            if reason:
                exempt.append({"file": str(path), "reason": reason})
                continue
            findings.append({"file": str(path),
                             "identifiers": sorted(set(hits))[:20],
                             "count": len(hits)})
        return json.dumps({
            "status": "clean" if not findings else "findings",
            "checked": checked,
            "clean": checked - len(findings) - len(exempt),
            "findings": findings,
            "exempt": exempt,
            "usage": "privacy_redact(paths=[...]) to fix; privacy_suspects(...) to "
                     "look for leak classes no rule covers yet.",
        }, indent=2)

    @mcp.tool()
    def privacy_redact(paths: Optional[List[str]] = None, dry_run: bool = False) -> str:
        """Rewrite shared content with identifying detail replaced by placeholders.

        Usernames and home paths become ``$USER`` / ``$HOME``, job ids and session
        UUIDs become ``<job-id>`` / ``<uuid>``, hostnames keep the cluster name and
        lose the node number. Citation lines pass through untouched — an author
        list is a public reference, and mangling it breaks the citation.

        ``.patch`` and ``.diff`` files are handled in a structure-preserving mode
        that replaces only the username segment of a path, so component counts and
        ``patch -pN`` strip levels survive.

        Args:
            paths: files or directories. Defaults to the entire layered store.
            dry_run: report what would change without writing.

        Returns JSON: {status, changed: [{file, identifiers}], unchanged, dry_run}.
        """
        from phronix.privacy import (STRUCTURED_SUFFIXES, anonymize, current_users,
                                     find_identifiers)

        users = current_users()
        changed, unchanged = [], 0
        for path in _targets(paths):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            clean = anonymize(text, extra_users=users,
                              preserve_structure=path.suffix in STRUCTURED_SUFFIXES)
            if clean == text:
                unchanged += 1
                continue
            hits = sorted(set(find_identifiers(text, extra_users=users)))[:20]
            if not dry_run:
                try:
                    path.write_text(clean)
                except OSError as exc:
                    changed.append({"file": str(path), "error": str(exc)})
                    continue
            changed.append({"file": str(path), "identifiers": hits})
        return json.dumps({
            "status": "ok",
            "changed": changed,
            "unchanged": unchanged,
            "dry_run": dry_run,
        }, indent=2)

    @mcp.tool()
    def privacy_suspects(paths: Optional[List[str]] = None, limit: int = 40) -> str:
        """Find content that *looks* identifying but no redaction rule covers yet.

        This is the discovery half of the privacy system. Everything the existing
        rules already handle is subtracted first, so what comes back is precisely
        the corner cases the current rules miss — a hostname shaped differently
        than expected, an internal URL, a token format nobody anticipated.

        A match here is a candidate, not a confirmed leak; several probes are
        deliberately noisy because a missed leak costs far more than a false
        positive. Review them, and when one is real, persist a rule with
        ``privacy_add_pattern`` so it is caught automatically from then on.

        Args:
            paths: files or directories. Defaults to the entire layered store.
            limit: maximum findings to return.

        Returns JSON: {status, count, suspects: [{file, probe, text}]}.
        """
        from phronix.privacy import current_users, suspects

        users = current_users()
        found = []
        for path in _targets(paths):
            if len(found) >= limit:
                break
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for probe, token in suspects(text, extra_users=users):
                found.append({"file": str(path), "probe": probe, "text": token})
                if len(found) >= limit:
                    break
        return json.dumps({
            "status": "ok" if found else "clean",
            "count": len(found),
            "suspects": found,
            "usage": "privacy_add_pattern(regex=..., replacement=..., reason=...) "
                     "for any of these that is a real leak class.",
        }, indent=2)

    @mcp.tool()
    def privacy_add_pattern(
        regex: str,
        replacement: str,
        reason: str,
        structure_safe: bool = True,
        layer: str = "",
    ) -> str:
        """Teach the redactor a new leak class, permanently.

        This is self-learning applied to privacy: a rule added here is stored as
        data in the layer's ``privacy_patterns.yaml``, ships to everyone who gets
        that layer, and applies to every future redaction without a code change.

        The regex is compiled before it is written — a rule that cannot compile is
        a rule that silently does nothing, and finding that out at redaction time
        means the leak already happened.

        Args:
            regex: Python regex matching the identifying text.
            replacement: what to substitute — a shell variable a reader can
                resolve (``$USER``) or an angle-bracket placeholder (``<token>``).
            reason: why this is identifying. Future readers need to know whether
                the rule is still right; a rule with no rationale never gets
                revisited.
            structure_safe: False if the rule changes a path's component count.
                Rules that are not structure-safe are skipped for ``.patch`` and
                ``.diff`` files, where they would break the patch.
            layer: force a target layer ("project", "user", "bundled").

        Returns JSON: {status, file, layer, regex}.
        """
        from phronix.privacy import add_pattern

        try:
            return json.dumps(
                add_pattern(regex, replacement, reason,
                            structure_safe=structure_safe, layer=layer or None),
                indent=2,
            )
        except Exception as exc:
            return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
