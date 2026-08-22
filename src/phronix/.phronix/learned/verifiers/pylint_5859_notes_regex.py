import re

def _build_pattern(notes):
    joined = "|".join(re.escape(n) for n in notes)
    return re.compile(rf"#\s*({joined})\s*(?=(:|\s|$))", re.I)

SPEC = {
    "kind": "skill",
    "target": "pylint-dev-pylint-5859",
    "claim": (
        "Replacing trailing \\b with \\s*(?=(:|\\s|$)) in the fixme regex "
        "makes punctuation-only note tags match, while normal tags keep matching."
    ),
    "assumptions": [],
    "inputs": [
        {"name": "pattern", "required": True,
         "resolve": lambda ctx: _build_pattern(["YES", "???", "TODO"])},
    ],
    "constraints": [
        {"name": "punctuation_tag_matches", "detail": "??? tag with message",
         "check": lambda ctx: (
             ctx["pattern"].search("# ???: no") is not None,
             "expected match on '# ???: no'")},
        {"name": "alnum_tag_matches", "detail": "TODO tag still matches",
         "check": lambda ctx: (
             ctx["pattern"].search("# TODO: do this") is not None,
             "expected match on '# TODO: do this'")},
        {"name": "punctuation_tag_no_message", "detail": "??? with no trailing text",
         "check": lambda ctx: (
             ctx["pattern"].search("# ???") is not None,
             "expected match on '# ???' (end of string)")},
        {"name": "no_match_on_unrelated_word", "detail": "should not match unrelated comment",
         "check": lambda ctx: (
             ctx["pattern"].search("# this is fine") is None,
             "expected no match on unrelated comment")},
    ],
    "invariants": [],
    "outputs": [],
}
