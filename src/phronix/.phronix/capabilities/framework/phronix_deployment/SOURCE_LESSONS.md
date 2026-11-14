# Lessons — phronix-deployment

Pitfalls and dated lessons for the **deploying the framework into a project and running its daemons** subject. Retrieved by *memory*
search (`context_memory`), not by skill search: "how do I do this" and "what went
wrong last time" are different questions, and keeping them in one file makes every
retrieval of either drag in the other.

## Pitfalls

### P1 — Editing a rendered agent or permission file

Both are regenerated. The change survives until the next deploy or sync, which is
long enough to look like it worked and short enough to be baffling when it stops.

### P2 — Expecting `--check` to cover the harness memory symlink

It deliberately does not. That link points into `~/.claude/projects/<slug>/`,
keyed on the project's absolute path, so a scratch comparison can never reproduce
it — including it would report drift forever on an up-to-date tree.

### P3 — Assuming a port is the configured one

When the configured port is held by another process the stack takes a free one
and persists it. Read the port from `phronix_stack status` or `env`, not from the
configuration.

## Lessons
