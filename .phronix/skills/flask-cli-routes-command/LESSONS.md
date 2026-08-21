# Lessons — flask-cli-routes-command

What went wrong before, and what it cost. Retrieved by **memory** search, not by
skill search: "how do I do this" and "what went wrong last time" are different
questions, and keeping them in one file makes every retrieval of either drag in
the other.

## Pitfalls

## Lessons

## Pitfalls

## Lessons

### L1 — Adding a Domain column broke test_simple/test_sort; also missed distinct Subdomain/Host semantics expected by tests

2026-08-21 — Attempt 1 for pallets__flask-5063 (feature request: show subdomain/domain info in `flask routes`) added an unconditional "Domain" column computed via a new `get_rule_domain()` helper (subdomain + SERVER_NAME, or just SERVER_NAME if no subdomain). Result: target tests test_cli.py::TestRoutes::test_host and test_subdomain still failed, AND it newly broke test_simple and test_sort (52/54 regressions passed, 2 failed).

Root cause of regressions: test_simple/test_sort call expect_order() which asserts on the literal start of each output line (e.g. line[:8] == "aaa_post"). Adding a new leading "Domain" column shifts all row content to the right, so those fixed-position substring checks fail.

Root cause of target test failure: test_host and test_subdomain check for the literal substrings "Host" and "Subdomain" in the header output (not "Domain").

Superseded speculation: this lesson originally guessed the column should be opt-in via a new CLI flag. The verified working approach (see I1/R1) instead makes the column conditional on `any(rule.host or rule.subdomain for rule in rules)`, with no new flag — so that guess was wrong and should not be followed.
