"""Redaction: what must be stripped, what must survive, and structure preservation.

The false-negative tests (things that must NOT be redacted) matter as much as the
positives. Over-redaction makes knowledge unusable and trains people to disable
the guard, which is how the real leaks get through.
"""
from __future__ import annotations

from phronix import privacy


class TestStripsIdentity:
    def test_home_paths(self):
        assert privacy.anonymize("/home/alice/proj/x.py") == "$HOME/proj/x.py"
        assert privacy.anonymize("/usr/workspace/bob/thing") == "$HOME/thing"

    def test_email(self):
        assert "<redacted-email>" in privacy.anonymize("contact alice.smith@example.com")

    def test_uuid_and_job_id(self):
        assert privacy.anonymize("run 550e8400-e29b-41d4-a716-446655440000") == "run <uuid>"
        assert "<job-id>" in privacy.anonymize("submitted fA1b2C3d4E5f6")

    def test_hostname_keeps_the_cluster_drops_the_node(self):
        assert privacy.anonymize("built on tuolumne1002") == "built on tuolumne<node>"

    def test_explicit_extra_username(self):
        """A bare username outside a path can only be caught if it is passed in."""
        assert privacy.anonymize("owner: jdoe", extra_users=["jdoe"]) == "owner: $USER"


class TestPreservesWhatIsNotIdentifying:
    def test_citations_pass_through(self):
        line = "**Authors:** Alice Smith, Bob Jones (alice@example.com)"
        assert privacy.anonymize(line) == line

    def test_version_strings_are_not_hostnames(self):
        """`rocm710` in a wheel tag is a build target, not a machine."""
        assert privacy.anonymize("torch==2.10.0+rocm710") == "torch==2.10.0+rocm710"

    def test_git_remotes_are_not_emails(self):
        assert privacy.anonymize("git@github.com:org/repo.git") == "git@github.com:org/repo.git"

    def test_existing_placeholders_are_not_re_redacted(self):
        """`/home/$USER` is the desired output; re-matching would corrupt it."""
        assert privacy.anonymize("$HOME/proj") == "$HOME/proj"
        assert privacy.anonymize("/home/$USER/proj") == "/home/$USER/proj"


class TestStructurePreservation:
    def test_diff_keeps_the_component_count(self):
        """Collapsing a path in a diff changes -pN and breaks the patch."""
        line = "--- a/home/alice/proj/x.py"
        plain = privacy.anonymize(line)
        structured = privacy.anonymize(line, preserve_structure=True)
        assert structured == "--- a/home/$USER/proj/x.py"
        assert structured.count("/") == line.count("/")
        assert plain.count("/") != line.count("/")

    def test_line_count_is_never_changed(self):
        text = "\n".join(["/home/alice/a", "safe", "/home/bob/b"])
        assert privacy.anonymize(text).count("\n") == text.count("\n")


class TestSuspects:
    def test_subtracts_what_the_rules_already_handle(self):
        """A path the redactor rewrites is not a corner case."""
        probes = {name for name, _ in privacy.suspects("/home/alice/proj")}
        assert "home-like path" not in probes

    def test_flags_a_class_no_rule_covers(self):
        found = privacy.suspects("token sk_livekeymaterial123")
        assert any(name == "api key-ish" for name, _ in found)

    def test_private_addresses_are_not_flagged(self):
        found = privacy.suspects("connect to http://127.0.0.1:8080/health")
        assert not any(name == "ip address" for name, _ in found)


class TestLearnedPatterns:
    def test_add_pattern_is_persisted_and_applied(self, isolated_layers):
        result = privacy.add_pattern(
            regex=r"ACME-\d{6}", replacement="<ticket>",
            reason="internal ticket ids identify the organisation",
        )
        assert result["status"] == "added"
        assert result["layer"] == "project"
        assert privacy.anonymize("see ACME-123456") == "see <ticket>"

    def test_duplicate_is_not_appended_twice(self, isolated_layers):
        privacy.add_pattern(r"ACME-\d{6}", "<ticket>", "reason")
        again = privacy.add_pattern(r"ACME-\d{6}", "<ticket>", "reason")
        assert again["status"] == "already_present"

    def test_invalid_regex_is_rejected_at_write_time(self, isolated_layers):
        """A rule that cannot compile silently does nothing; fail loudly instead."""
        import pytest

        with pytest.raises(Exception):
            privacy.add_pattern("([unclosed", "<x>", "reason")

    def test_structure_unsafe_rules_are_skipped_for_diffs(self, isolated_layers):
        privacy.add_pattern(r"/data/\w+/", "$DATA/", "reason", structure_safe=False)
        assert privacy.anonymize("/data/alice/x") == "$DATA/x"
        assert privacy.anonymize("/data/alice/x", preserve_structure=True) == "/data/alice/x"


def test_find_identifiers_reports_without_mutating():
    text = "/home/alice/x and bob@example.com"
    hits = privacy.find_identifiers(text)
    assert any("/home/alice" in h for h in hits)
    assert any("bob@example.com" in h for h in hits)


class TestFixtureExemption:
    """The one legitimate case: a corrector that tests the redactor must contain
    the inputs it redacts. Without an exemption the sweep is permanently
    non-clean, and a check that is always yellow is a check people stop reading."""

    def test_a_marker_with_a_reason_exempts(self):
        text = ('"""Doc.\n\nphronix: privacy-fixture — synthetic inputs for the redactor.\n"""\n'
                '/home/someone/x\n')
        assert privacy.exemption_reason(text) == "synthetic inputs for the redactor."

    def test_a_marker_without_a_reason_does_not_exempt(self):
        """The point is that someone can later judge whether it is still warranted."""
        assert privacy.exemption_reason('"""phronix: privacy-fixture\n"""\n') is None

    def test_a_marker_buried_mid_file_does_not_exempt(self):
        text = "\n".join(["filler"] * 60 + ["phronix: privacy-fixture — sneaky"])
        assert privacy.exemption_reason(text) is None

    def test_an_unmarked_file_is_not_exempt(self):
        assert privacy.exemption_reason("/home/someone/x\n") is None

    def test_the_bundled_privacy_verifier_is_exempt_and_still_scanned(self, isolated_layers):
        from phronix.layers import bundled_root

        path = bundled_root() / "verifiers" / "privacy_rules_hold.py"
        text = path.read_text()
        assert privacy.exemption_reason(text)
        # Exempt from BLOCKING, not from detection: the identifiers are still found.
        assert privacy.find_identifiers(text)
