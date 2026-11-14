# Lessons: phronix_privacy

- [L-37925610] A realistic username in a documentation example -> The most common way a skill fails its own privacy check. Use `<user>`, `<host>`, `<job-id>` — placeholders are exempt from redaction by design. -> follow phronix-privacy P1 (Corner cases) (2026-09-15, dftracer-agents phronix-privacy/LESSONS.md P1)
- [L-59bcad3f] Fixing the file instead of the rule -> The class stays open and the next session reintroduces it, usually somewhere less visible. `privacy_add_pattern` is the fix. -> follow phronix-privacy P2 (Corner cases) (2026-09-15, dftracer-agents phronix-privacy/LESSONS.md P2)
- [L-9b985947] Skipping `privacy_suspects` because `privacy_scan` was clean -> A clean scan means the *known* rules found nothing. It says nothing about the leak classes nobody has encoded yet, and those are the ones that matter. -> follow phronix-privacy P3 (Corner cases) (2026-09-15, dftracer-agents phronix-privacy/LESSONS.md P3)
