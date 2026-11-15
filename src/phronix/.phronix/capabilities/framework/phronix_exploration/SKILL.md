---
name: phronix_exploration
description: Foreground -> background learning. Everything the agent does by hand (Bash, Python scripts, reads, edits) and every foreground turn is recorded and queued for the background learner, which turns it into capabilities and lessons. Load to mark the success point of a manual exploration (exploration_complete), or when you are the background learner working through the queue.
---

# Foreground work becomes capabilities

Cross-references: [[capability_builder]] [[lessons]] [[tools_parallel]]

## Rules
- In the foreground, use a capability before working anything out by hand. What you do by hand anyway (shell commands, Python scripts, reads, edits, fetches) is recorded automatically by hooks, per chat, across turns and sub-agents; nothing to call for that.
- The moment a manual exploration is verified to work (it builds, the run finishes, the probe answers, the fix holds), call `exploration_complete` with the goal and the verification, then keep working. Without it the end of the turn decides (enough manual steps, the last ones succeeded, the reply reports no failure).
- Every foreground turn is queued as well: what the user said there (a correction, a preference, a choice) is learning.
- A plain phronix install runs the background agents itself: `phronix sync hooks` installs the recorder, whose Stop hook starts `phronix-learner kick` (headless Claude Code) when work is due; `phronix-learner status` shows the queue and the runs. A project with a web UI (moirai-agents, rabbit-agent) runs them from its server instead.
- The background learner claims a batch, reads it with `exploration_list(status='claimed', forge=<run>, full=true)`, stages proposals, and closes every record with `exploration_mark`; `exploration_validate(forge=<run>)` at the end.

## Constraints
- The APPROVAL POLICY at the end of the learner's ask decides what happens to what it stages. Automatic (the default): apply what passes its checks (`capability_apply(id, confirmed=true)`, `lesson_decide(id, approve=true)`), keep the store consistent (one copy of each fact, no contradicting rules), and ask the user (`consolidation_ask`) only what the evidence cannot decide. Review (<P>_LEARN_APPROVAL=review): everything waits for the user.
- A background run is never recorded (its <P>_BACKGROUND is set): the learner does not learn from itself.
- Keep only the path that worked; no usernames, job ids or node names in what is proposed.

## Corner cases
- `analysis.bypassed`: a capability already does this and the chat did it by hand. That is not `covered`: find why (it failed, lacked an option, was not known) and stage the fix.
- `analysis.self_edits`: the agents' own code was patched from a chat. A tool was broken: report the issue and mark `issue`.
- A record claimed by a run that died comes back after its claim expires; after three claims it stays until someone marks it.

## Parallel plan

Independent subjects in a batch are learned in parallel: lookups (knowledge_search, capability_get) for every candidate go out in one message. Sequential, and why: `exploration_mark` comes after the proposal it names exists, and `exploration_validate` after every mark. Larger fan-outs build on [[tools_parallel]].

## Corrector
Predictor `exploration_mark`, validator `exploration_validate`. A failed verdict names the record and the fix: mark what is unmarked, name the capability and proposal for new/update/bypassed. The same failure twice stops the loop: leave it for the user in the report.

## Self-heal
- `exploration_mark` refused: read the refusal, it names the bypass, gap or self-edit left unanswered; answer it and mark again.

## Self-learn
- Anything new explored here (workload, software, tool, system) becomes a capability: `capability_builder`, Rules.
