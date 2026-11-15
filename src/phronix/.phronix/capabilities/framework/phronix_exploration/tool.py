"""phronix_exploration: what the agent does in the foreground goes to the background learner.

The recorder hooks (phronix.engine.explore_hook) queue every manual exploration at its success point and every
foreground turn; the background learner (phronix.engine.background) claims a batch and turns it into capability and lesson
proposals. These are the tools both sides use: the foreground marks a success point, the learner reads its batch,
gives its verdict per record, and reviews slow tools."""
from phronix.engine import explore as X
from phronix.engine import verdict as V


def _validate(forge: str = "") -> dict:
    v = V.Verdict("exploration")
    rows = [e for e in X._all() if not forge or e.get("forge") == forge]
    v.assume("records", bool(rows), "no queued foreground work" + (f" for learner run {forge}" if forge else ""))
    for e in rows:
        st, i = e.get("status"), e.get("id")
        if forge:
            v.check(f"{i}:marked", st == "processed", f"{i} is {st}",
                    "exploration_mark it: every claimed record needs a verdict")
        if st == "processed":
            outs = set((e.get("outcome") or "").split(","))
            v.check(f"{i}:outcome", bool(outs - {""}), "processed without an outcome", "exploration_mark it again")
            if outs & {"new", "update", "bypassed"}:
                v.check(f"{i}:proposal", bool(e.get("capability") and e.get("proposal")), e.get("outcome", ""),
                        "name the capability and the proposal id staged for it")
        elif e.get("attempts", 0) >= X.MAX_ATTEMPTS:
            v.check(f"{i}:attempts", False, f"{X.MAX_ATTEMPTS} learner runs claimed it and none marked it",
                    "read it with exploration_list(full=true) and mark it (nothing + why, if it cannot be learned)")
    return v.result()


def register(mcp):
    @mcp.tool()
    def exploration_complete(goal: str, verification: str, subject: str = "", what_worked: str = "", commands: str = "",
                             family: str = "") -> dict:
        """Mark the SUCCESS POINT of a manual exploration: the moment what you worked out by hand (a build, a run, a probe, a fix, a procedure, a
        Python or shell script) is verified to work. Everything you did by hand in this chat since the last completion is queued for the background
        learner, which turns it into a new or updated capability (a proposal for the user's approval) so nobody has to explore it again. Call it
        right after the verification, then keep working. goal: what it was for; verification (required): the command/output/test that shows it
        works; subject: the workload/software/tool/system; what_worked: the path that worked (not the dead ends); commands: the exact commands
        that worked, in order; family: workload|software|tools|system. Returns {status, queued_at_end_of_turn}."""
        return X.mark_complete(goal, subject, what_worked, commands, verification, family)

    @mcp.tool()
    def exploration_list(status: str = "", forge: str = "", limit: int = 50, full: bool = False) -> dict:
        """List the foreground work queued for the background learner and its outcomes. status: complete (waiting) | claimed (a learner run has it)
        | processed; forge: the learner run id; full=true returns every step, prompt, transcript path, completion summary and the deterministic
        `analysis` (bypassed capabilities, gaps, self-edits) - what the learner needs. Returns {status, counts, explorations, dir}."""
        return X.listing(status, forge, int(limit or 50), bool(full))

    @mcp.tool()
    def exploration_mark(ids: list, outcome: str, capability: str = "", proposal: str = "", note: str = "") -> dict:
        """The background learner's verdict on queued records (every claimed id must be marked). outcome: one or more, comma-separated: new |
        update (a capability proposal was staged: capability + proposal id) | bypassed (a capability existed but the chat did its work by hand:
        capability + the proposal that fixes why and makes it be used) | lesson (say which in note) | issue (the agents' own code was patched from
        the chat: the tool issue was reported) | covered (the chat USED the existing capability) | nothing (not reusable: why). Checked against
        the record's analysis: unanswered bypasses, gaps or self-edits are refused. Returns {status, marked, unknown, refused}."""
        return X.mark(list(ids or []), outcome, capability, proposal, note)

    @mcp.tool()
    def exploration_validate(forge: str = "") -> dict:
        """Rule on the learner's work: every claimed record of learner run `forge` is marked, every processed record has an outcome, every new/update/
        bypassed names its capability and proposal, and no record was claimed and dropped too often. Use at the end of a learner run.
        Deterministic. Returns {status: pass|fail|inconclusive, failed: [{name, detail, fix}], passed, total}."""
        return _validate(forge)

    @mcp.tool()
    def slow_steps(min_seconds: float = 0, days: float = 7, include_reviewed: bool = False) -> dict:
        """Tools whose typical call is SLOW across chats (from recorded timings): median/max/total seconds, calls, how often they ran alone, the
        capability providing them, example inputs. The background learner uses it to make slow capabilities parallelize. min_seconds: median
        threshold (default <P>_SLOW_S, 60); days: look-back (7); include_reviewed: also tools already reviewed. Returns {status, slow, threshold_s}."""
        return X.slow_steps(float(min_seconds or 0), float(days or 7), bool(include_reviewed))

    @mcp.tool()
    def slow_step_mark(tool: str, outcome: str, capability: str = "", proposal: str = "", note: str = "") -> dict:
        """The learner's verdict on a slow tool from slow_steps: proposed (a capability_update that parallelizes it was staged: capability +
        proposal id), issue (not a capability: the tool issue was reported - say so in note), already_parallel (say what bounds it), inherent (one
        indivisible job such as a compile or a job wait - say why). Returns {status, tool, outcome}."""
        return X.slow_step_mark(tool, outcome, capability, proposal, note)
