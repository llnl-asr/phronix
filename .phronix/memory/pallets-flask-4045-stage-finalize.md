---
name: pallets-flask-4045-stage-finalize
description: Stage finalize results for pallets/flask-4045 task
metadata:
  type: project
---

**Why:** The previous attempt failed to raise errors for dotted blueprint names and suffered from Werkzeug's `EnvironBuilder` signature change (`as_tuple` removed).
**How to apply:** Add validation in Flask's blueprint registration to reject names containing a dot, mirroring endpoint validation. Update Flask testing client to avoid passing `as_tuple` to Werkzeug; adjust `src/flask/testing.py` to be compatible with current Werkzeug version.
**Reproduction:** See `tmp/research/repro.sh` for a script that reproduces the failing tests.
