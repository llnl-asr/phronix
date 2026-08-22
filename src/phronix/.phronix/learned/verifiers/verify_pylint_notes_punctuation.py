from pathlib import Path

SPEC = {
    "kind": "skill",
    "target": "pylint-notes-punctuation",
    "claim": "The regex for note tags in pylint/checkers/misc.py does not include a trailing word-boundary \\b; punctuation-only tags are recognized by pylint's --notes option.",
    "assumptions": [],
    "inputs": [
        {
            "name": "source",
            "required": true,
            "resolve": lambda ctx: (Path.cwd() / "pylint/checkers/misc.py").read_text()
        }
    ],
    "constraints": [
        {
            "name": "no_word_boundary",
            "detail": "regex_string assignments lack trailing \\b",
            "check": lambda ctx: all("\\b" not in line for line in ctx["source"].splitlines() if "regex_string" in line)
        }
    ],
    "invariants": [],
    "outputs": []
}
