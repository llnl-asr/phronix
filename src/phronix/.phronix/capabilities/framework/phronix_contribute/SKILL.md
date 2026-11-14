---
name: phronix_contribute
description: Pull latest, push and switch this project's contributions to the projects upstream of it (phronix, dftracer-agents), merging conflicts; load when the user asks to pull, push, rebase or contribute back.
---

# phronix_contribute

Each upstream (phronix, dftracer-agents) runs from a clone in this project's `vendor/`. The clone always stays on the
upstream's integration branch (`develop` for dftracer-agents, else the remote's default). What this project learns
about a capability the upstream owns is committed there as a local commit, ahead of `origin/<branch>`. It reaches the
upstream through a pull request from a branch made only when pushing.

## Rules
- Pull latest through `contrib_rebase`: it replays the local commits on `origin/<branch>`, merging conflicts.
- Push only through `contrib_push`: it pulls latest first, then pushes the unpushed commits on a NEW branch
  `contrib/<this project>-<date-time>`; the clone stays on its branch. Give the user the `pull_request` link.
- After the push, `contrib_switch` returns the clone to `origin/<branch>` (develop). It refuses while a local commit is
  on no pushed branch.
- Never `git rebase`, `git merge`, `git push` or `git checkout` by hand in an upstream clone.
- `contrib_refresh` fetches and says what to do next (switch, pull latest, push, open the pull request, nothing).
- After every call, `contrib_check` on its result.

## Constraints
- Lessons (`LESSONS.md`), worked entries (`WORKED.md`) and `capability.json` merge by themselves: every entry from
  both sides is kept, histories are joined, the version is the higher one.
- Anything else is merged by the agent; its merge must parse and carry no conflict markers, or the rebase is aborted
  and the clone stays as it was.
- Nothing is pushed to the upstream's integration branch, and no pull request is opened automatically.

## Corner cases
- A clone not on its integration branch is not pulled: `contrib_switch` first (it refuses if commits would be lost).
- Uncommitted changes in a clone stop pull and switch: they came from a change that did not finish.
- Nothing unpushed: push does nothing and reports the last pull-request link, if any.

## Parallel plan

Independent calls go out together in one message: `contrib_status` while other work runs. Sequential, and why:
`contrib_rebase` / `contrib_push` / `contrib_switch` change the clone, and `contrib_check` rules on what they returned.

## Corrector
- `<project>:rebased` fails: call `contrib_rebase` again with merge_with_agent=true; if the agent's merge is refused,
  read the listed conflicts, merge them by hand in the clone, then pull again.
- `<project>:pushed` fails: read push_error (credentials, network), fix it, `contrib_push` again.
- `<project>:pull_request` fails: open the pull request from the pushed branch on the upstream's page.

## Self-heal
- If a tool here is wrong, update this capability; do not pull or push by hand.

## Self-learn
- What is explored here becomes a capability: a new kind of conflict that merges deterministically belongs in the engine.

## What works
- 2026-11-13: lesson-only contributions rebase onto a rewritten upstream with no agent; a code conflict is merged by
  the agent and pushed with its pull-request link.
- 2026-11-14: clones stay on develop; each push makes a dated branch and returns the link that opens the pull request.
