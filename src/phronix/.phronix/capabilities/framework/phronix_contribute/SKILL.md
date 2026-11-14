---
name: phronix_contribute
description: Push and rebase this project's contributions to the projects upstream of it (phronix, dftracer-agents), merging conflicts; load when the user asks to push, rebase or contribute back.
---

# phronix_contribute

What this project learns about a capability another project owns is committed on `contrib/<this project>` in a
worktree of that project's clone (`vendor/contrib/<project>`). It reaches the other project through a pull request.

## Rules
- Push only through `contrib_push`: it rebases first, so the pull request applies to the upstream's current version.
- Rebase through `contrib_rebase`; never `git rebase`, `git merge` or `git push` by hand in a contribution worktree.
- Only the contribution commits are replayed (the base they were made on is recorded), so a rewritten upstream never
  brings back an old commit.
- After every call, `contrib_check` on its result; give the user the pull-request links it reports.

## Constraints
- Lessons (`LESSONS.md`), worked entries (`WORKED.md`) and `capability.json` merge by themselves: every entry from
  both sides is kept, histories are joined, the version is the higher one.
- Anything else is merged by the agent; its merge must parse and carry no conflict markers, or the rebase is aborted
  and the branch stays as it was.
- The branch is pushed with `--force-with-lease` (it is rebased); it is never pushed to the upstream's main branch.

## Corner cases
- A clone with local changes is not fast-forwarded: the rebase uses what it has; say so to the user.
- Uncommitted changes in a contribution worktree stop the rebase: they came from a change that did not finish.
- Nothing ahead: nothing is pushed and there is no pull request to open.

## Parallel plan

Independent calls go out together in one message: `contrib_status` while other work runs. Sequential, and why:
`contrib_rebase` / `contrib_push` change the branch, and `contrib_check` rules on what they returned.

## Corrector
- `<project>:rebased` fails: call `contrib_rebase` again with merge_with_agent=true; if the agent's merge is refused,
  read the listed conflicts, merge them by hand in the worktree, then rebase again.
- `<project>:pushed` fails: read push_error (credentials, someone else changed the branch), fix it, `contrib_push` again.
- `<project>:pull_request` fails: open the pull request from the branch on the upstream's page.

## Self-heal
- If a tool here is wrong, update this capability; do not rebase or push by hand.

## Self-learn
- What is explored here becomes a capability: a new kind of conflict that merges deterministically belongs in the engine.

## What works
- 2026-11-13: lesson-only contributions rebase onto a rewritten upstream with no agent; a code conflict is merged by
  the agent and pushed with its pull-request link.
