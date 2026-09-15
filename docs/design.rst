==========================
phronix — design document
==========================

:Status: living document, kept in step with the code
:Audience: someone who will change phronix, or judge whether to trust it

.. contents::
   :local:
   :depth: 2


What phronix is
===============

phronix is a framework for agents that get better at a codebase over time
instead of starting from zero every session. It rests on one claim:

   An agent's knowledge should be **durable, retrievable, and checkable**.

Three mechanisms follow from that, and everything in the codebase is one of
them or serves one of them.

**Self-research.** Before attempting unfamiliar work, find out how the work
should be done — externally, not only from the code in front of you — and turn
the answer into infrastructure rather than into an answer.

**Self-learning.** After doing work, record what generalises: a lesson into a
skill, a durable fact into memory, a deterministic procedure into code.

**Self-healing.** When something is wrong — a broken tool, a failed approach —
fix the thing itself rather than working around it, and record what was ruled
out so the next session does not re-derive it.

The unifying discipline is **predictor/corrector**. Learning and healing are
*predictions*: "this is how it works", "this fix will hold". A corrector is a
deterministic check that says whether the prediction still holds — same verdict
on every machine, forever, with no model in the loop. A claim nobody can
falsify is a liability in a shared knowledge base, because it gets trusted long
after it stops being true.


Why the knowledge is a database, not notes
==========================================

The tempting design is a folder of markdown notes an agent greps. It fails in
a specific way: notes accrete, retrieval returns whole documents, context fills
with things that are almost relevant, and nobody can tell whether an entry is
still true.

phronix instead treats knowledge as a small relational database expressed in
markdown, with stable keys, a catalogue, and typed relations.

Skills: one subject, labelled blocks
------------------------------------

A **skill** is one subject and only one. It has two files:

``SKILL.md``
   The Index, plus labelled blocks: ``I*`` instructions, ``R*`` rules, ``X*``
   references. This is what *skill search* returns — how to do the thing.

``LESSONS.md``
   ``P*`` pitfalls and ``L*`` lessons. This is what *memory search* returns —
   what went wrong before.

The split is not tidiness. "How do I do this?" and "what went wrong last time?"
are different questions asked at different moments; keeping them in one file
means every retrieval of either drags in the other, and the file grows until no
part of it can be loaded alone.

Labels (``I3``, ``R2``) are **stable keys**. They are allocated from the highest
number in use and never recycled, because a reused label silently redirects
every existing cross-reference to different content — the exact failure stable
keys exist to prevent. Cross-references are wiki-links with a label, so
``[[phronix-privacy#R4]]`` is a foreign key into another skill's row.

The Index is a generated catalogue: label, section, and a ``covers`` phrase.
It is regenerated on every write, so the catalogue cannot drift from the file.

Enforced constraints
--------------------

Structure that is merely requested is structure that decays. These are checked
at write time:

``BLOCK_LIMITS``
   ``rule`` 1000 characters, ``instruction``/``reference`` 1400, ``lesson``/
   ``pitfall`` 3000. Over-long blocks are **rejected**, with a message naming
   the limit and the remedy, not truncated — a silently cut body is a
   half-sentence presented as complete knowledge.

   This limit exists because of a measured failure: a run wrote a 12 KB skill
   whose correct fix sat as a sub-bullet inside one instruction. Three later
   attempts retrieved that skill and none acted on it. The signal was present
   and its length destroyed it.

One subject per skill
   Enforced socially rather than mechanically, but the retrieval design makes
   violations expensive: a skill covering two subjects matches both and returns
   the wrong blocks for each.


Retrieval: index first, then blocks
===================================

``phronix.skills.search`` runs in two phases.

1. **Index.** Score each skill's subject, description and Index rows. This
   answers "which subject is this question about?" without block bodies voting.
2. **Expand and match.** Fold the matched rows' ``covers`` text into the query,
   then score blocks with the expanded terms. Index rows describe the subject
   in the skill's own vocabulary, which is usually not the asker's; that
   expansion bridges the two.

Only ``covers`` is scored, never the ``section`` column — it holds one of three
fixed values, so scoring it made every query containing "rule" or "reference"
match the entire library.

Relevance is weighted by rarity
-------------------------------

A match must account for at least ``MIN_TERM_COVERAGE`` (0.30) of a query's
*discriminating power*, where each term is weighted by inverse document
frequency.

Plain term counting fails in both directions, and both were observed:

* "pylint recursive mode ignoring ignore-paths configuration" matched five
  framework skills on the single generic word **"mode"** and looked like a hit;
* "redact usernames and home paths before writing" matched ``phronix-privacy``
  on 2 of 6 terms and looked like a miss.

Rarity separates them: "mode" appears in most skills and weighs ~0.1; "usernames"
appears in one and weighs ~2.6. Measured separation on real queries is wide —
irrelevant domain queries land at 0.14–0.17, genuinely relevant ones at
0.62–1.00.

**Returning nothing is a feature.** An empty result tells an agent it is the
first to meet this problem — true, useful, and cheap. Five irrelevant skills
tell it the system has knowledge, cost thousands of tokens of context to
disprove, and teach it that searching is not worth doing.


Layers: where knowledge lives
=============================

Three layers, resolved highest-first, each holding the same
``CONTENT_DIRS``: ``skills``, ``agents``, ``memory``, ``capabilities``,
``verifiers``, ``research``.

============  ===========================  =============================================
layer         location                     role
============  ===========================  =============================================
bundled       inside the installed wheel   what phronix ships with
user          ``~/.phronix``               learned across this person's projects
project       ``<repo>/.phronix``          learned by this repository; committed
============  ===========================  =============================================

A higher layer shadows a lower one wholesale by name, rather than merging block
by block: partial merges produce documents no author ever wrote, and debugging
them means reasoning about three files at once.

Writes go to the project layer by default, so knowledge travels with the code it
is about, in the same commit and the same review. ``resolve_write_layer`` guards
against a phronix checkout installed in editable mode capturing another
project's learning.

The bundled layer lives at ``src/phronix/.phronix`` and is tracked in git, with
``.phronix`` at the repository root a symlink to it. Keeping it under ``src/``
is what makes it ship inside the wheel; keeping it in git is what makes the
shipped knowledge reviewable in the same way as the code. The symlink exists so
that a tool run from the root finds the store where it expects it.

Carried knowledge — what a previous run promoted — belongs in the carry root
rather than the packaged layer. A run that wrote its learning into the installed
package would grow the wheel with every task and leave the working tree dirty
mid-run.


Capabilities: deterministic work becomes code
=============================================

A **capability** is an MCP tool authored at runtime and stored in a layer, not
in the wheel — an installed wheel is read-only, and learning that could only be
written into it would not be learning.

The rule is simple: *a deterministic procedure described in prose is a procedure
that will be performed differently next time.* If a step has one right answer
for given inputs, it becomes code via ``capability_new``, and prose describes
only the decisions.

Past a threshold they are dispatched, not registered
----------------------------------------------------

A capability is an MCP tool, and every registered tool's schema is re-sent on
every request. A store that has been learning for a while therefore competes
with the task for the context it is supposed to be helping with: measured at
1,150 learned tools, the schemas crowded out the work.

So the registration is conditional. Up to ``DISPATCH_THRESHOLD`` (64)
capabilities are published as ordinary MCP tools, one schema each. Past it they
are reached through a single ``capability_call(name, arguments)`` and no
per-capability schema is published at all. The choice is made once, before
anything is imported, from the number of visible capabilities — a capability
must be reachable the same way as its siblings, or an agent cannot tell from
one call how to make the next.

Two consequences worth knowing:

* **The calling convention changes with the size of the store.** Anything that
  reads a transcript to see which capabilities were used must recognise both
  shapes. A metric that matched only the direct form silently reported zero
  reuse for every run after the dispatcher landed, while the traces plainly
  showed the tools being called.
* **One broken capability must not take the server down.** A module that fails
  to import is caught, reported with its traceback, and skipped. A server that
  refuses to start because of one bad learned tool would make the framework's
  own learning the thing that bricks it.


Verification: the corrector half
================================

Every learned thing is a prediction; a verifier is its corrector. Verifiers are
deterministic Python, and the five facets are the contract:

===========  ================================================================
facet        what it establishes
===========  ================================================================
assumptions  the preconditions the claim needs (gating)
inputs       what it operates on is present and well-formed (gating)
constraints  limits that must hold
invariants   properties that must not change
outputs      what it produces is what it promised
===========  ================================================================

``assumptions`` and ``inputs`` are **gating**: when they fail the verdict is
``inconclusive``, not ``fail``. A check that could not run has not found a
defect, and reporting one would train people to ignore verdicts.

Statuses are ``pass``, ``fail``, ``inconclusive``, ``error``, aggregated
worst-first as ``fail`` > ``error`` > ``inconclusive`` > ``pass``. ``error`` is
kept distinct from ``fail`` because a broken verifier and a broken claim need
different responses.

``verify_coverage`` reports what has *no* verifier at all, since the most
dangerous claim is the one nobody thought to check.


Self-research
=============

The step that goes missing when an agent is capable enough to start
immediately. Observed: given an unfamiliar bug, an agent opens the file it first
suspects, writes a plausible fix, fails, and — with a learning loop attached —
records steadily more detailed notes about that same file. Three attempts, one
location, and the real fix one line away in a module nobody opened.

Gate, then strategy
-------------------

``research_assess`` is deterministic: it counts matching blocks in the
catalogue, so "do I already know this?" is a lookup rather than a matter of the
model's confidence — which is the signal that is wrong in exactly the case that
matters. Fewer than ``MIN_BLOCKS_FOR_COVERAGE`` (2) blocks is a ``gap``.

On a gap, the strategy runs **in this order**, and the order is the substance:

1. **Characterise the subject** — library defect, tool usage, algorithm/format,
   or environment problem. Each sends you somewhere different.
2. **Search outside the checkout, before reading the code.** For a defect: the
   issue as filed, whether it was fixed upstream, the commit that fixed it. For
   a tool: its documentation and ``--help``, the exact option, its default and
   interactions, then a worked example.
3. **Ground it locally** — locate each candidate's code path *at this version*
   and confirm the code matches what the source implies.
4. **Measure.**

Reading the code first anchors the agent to whichever file it opened, after
which every search becomes a search for confirmation.

The stages, and which of them may be cut short
----------------------------------------------

A research pass is a fixed sequence of agent invocations, each with its own
budget. The first pass explores; every later one diagnoses.

==================  ======  ==========================================================
stage               budget  what it is for                                            
==================  ======  ==========================================================
``survey``          180     what is already known, here and upstream                  
``plan``            600     the figure of merit, the corpus and its split, the aspects
``aspect`` ×N       540     investigate one question — *and try what it turns up*     
``aspect-record``   420     file what an aspect found; a guarded clock, not a budget  
``aspect-recheck``  150     confirm a settled finding still applies at this version   
``collect``         480     three investigations become one account                   
``propose``         600     candidate approaches, two to four, genuinely different    
``tune`` ×N         600     measure on train+validate, refine, measure again          
``evaluate`` ×N     240     score on the held-out set, once, changing nothing         
``execution-plan``  600     write the plan, build its tools; the skill comes out      
``diagnose``        600     *retries only*: reproduce, refine, re-measure             
==================  ======  ==========================================================

``survey``            180  what is already known, here and upstream
``plan``              600  the figure of merit, the corpus and its split, the aspects
``aspect`` ×N         540  investigate one question — *and try what it turns up*
``aspect-record``     420  file what an aspect found; unbudgeted work, guarded clock
``aspect-recheck``    150  confirm a settled finding still applies at this version
``collect``           480  three investigations become one account
``propose``           600  candidate approaches, two to four, genuinely different
``tune`` ×N           600  measure on train+validate, refine, measure again
``evaluate`` ×N       240  score on the held-out set, once, changing nothing
``execution-plan``    600  write the plan and build its tools; the skill comes out
``diagnose``          600  *retries only*: reproduce the failure, refine, re-measure
=================  ======  ==========================================================

The parallel stages — ``aspect``, ``tune``, ``evaluate`` — explore. Three run at
once and one cut short costs that branch and nothing else.

The rest is connective tissue, and ``MUST_FINISH_STAGES`` marks it: ``plan``
decides what the investigation will even look at, ``collect`` is where three
investigations become one account, ``propose`` turns that account into
candidates, ``diagnose`` is a retry's whole job, and ``execution-plan`` writes
the skill that is the entire durable output. Truncating one of those does not
lose a branch, it loses the flow — a ``collect`` cut half way discards what three
investigators spent 700 seconds finding, and ``propose`` then works from a
partial summary. Their ceilings are hang-guards, not work budgets, and
``status.sh`` reports a truncated one as a defect rather than as normal.

The figure of merit, fixed in advance
-------------------------------------

``research_define_fom(topic, name, direction, target, measure)`` declares the one
number that decides, before any approach is compared. A criterion chosen after
the results are in is a justification, not a test. ``measure`` is mandatory: a
figure of merit nobody can re-derive cannot be checked, and an unfalsifiable
criterion lends the appearance of rigour to an unmeasured choice.

It cannot be renamed once anything is measured against it. ``rank_approaches``
reads each approach's metric *by name*, so renaming the criterion silently
unscores every measurement taken under the old one: those approaches then sort
below candidates with worse numbers and below candidates nobody measured at all.

Measured, across three consecutive runs of pylint-7080: a refinement carrying
the correct fix scored 1.0 under ``recursive_discovery_ignore_accuracy``, a
later stage redeclared the metric as ``files_correctly_filtered``, and the
refinement ranked below a 0.5. The attempt implemented something else and failed
the same way each time. ``define_fom`` now refuses the rename and names the
approaches that would be unscored; re-declaring the same metric stays
idempotent, and changing it before anything is measured is still free.

Approaches are potential until the tests say otherwise
------------------------------------------------------

Every approach is recorded with a ``source`` and enters as ``potential``. It
becomes ``working`` only when the task actually passes with it, and
``falsified`` when it was built and measured and did not work. **No status is
reachable by argument.**

This replaced an earlier design that ranked predicted scores and spent the
attempt on the winner. That design failed invisibly: two runs of the same task,
same model, same prompts, each asserted the top score for a *different*
approach, each was trivially its own argmax, and the corrector reported ``pass``
for both — while only one of the patches fixed anything. An argmax over
predictions returns whatever the agent already believed.

So candidates are **built in parallel**, one agent each, in separate containers
and checkouts, and judged by the same evaluator. The one that passes is marked
``working``; the rest are ``falsified`` and never spend an agent again.

A failure names an approach, and ``research_add_approach`` then refuses that
name outright. Prompt-level discouragement was not enough: one task re-proposed
a single wrong idea across four attempts, each round rediscovering that it did
not work, because nothing on the write path could tell "not tried yet" from
"tried and lost".

Refinement: right idea, wrong extent
------------------------------------

Blanket refusal turned out to be too blunt in the other direction. A pylint task
failed with the ignore check added to exactly the right function, on exactly the
right line, and no path normalisation — so ``./ignored_subdirectory/failing.py``
never matched an anchored pattern. The idea was right and one call short, and
banning the name sent the next attempt looking elsewhere, away from an answer it
was a line from having.

Two failures wear the same status and the test output tells them apart:

* the change never ran, or ran and the behaviour was untouched — the idea is
  wrong, and the refusal is correct;
* the change ran, in the right place, and missed a specific case — the idea is
  right, and what it needs is the missing case, not a replacement.

``research_refine_approach(topic, key, diagnosis, change)`` takes the second
path. It records a **new** approach with its own key, linked to the parent by
``refines``, the parent marked ``superseded_by``. Deliberately expensive to
call: the ``diagnosis`` must say what the failure output actually showed and the
``change`` what will be different, both checked for substance, because without
them this is the rename the refusal exists to stop.

A revision starts **unmeasured**. Inheriting the parent's metrics would let a
score obtained by the version that failed rank the version that replaced it,
which is the one comparison this must not allow.

And refinement is bounded — ``MAX_REFINEMENTS`` is 2. "Nearly right, one more
tweak" is available forever if nothing stops it, and an unbounded version of
this becomes the failure it was built to fix: one idea consuming every remaining
attempt. Past the bound the diagnosis is what is wrong, not the implementation.

Aspects try what they find
--------------------------

The aspect stage investigates in parallel, one agent per independent question.
It used to be read-only, which meant every candidate reached the ranking as a
*prediction* and the first real measurement happened two stages later.

That failed in a specific, repeatable way: a research pass would end with its
top-ranked approach scoring **0.0** and every other candidate unmeasured — so
the attempt implemented the only thing carrying a number, and the number said it
did not work. ``research_choose`` already refuses to select on predictions; the
flow simply had nowhere earlier to produce anything better.

So each aspect now gets its own git worktree and is told to change the code and
see: run the **train** and **validate** instances, record trials, and record the
approach with ``measurement`` naming the commands behind the numbers. An idea
that falls short is refined and measured again rather than abandoned. This is
the cheapest point in the flow to produce a measured candidate — the agent is
already in the code, and the corpus was declared by ``plan`` before aspects
started.

The worktree is what makes it safe. Three concurrent agents editing one checkout
each measure a mixture of everybody's edits; and the aspects must not touch the
tree the attempt is diffed from. One helper builds them for aspects and
evaluators alike, symlinking ``.opencode`` in — without it the agent comes up
with no phronix tools at all and cannot record a trial, which fails quietly as
"scores that turn out to be predictions".

Tuning and scoring are different stages, on different instances
---------------------------------------------------------------

Refinement is only useful where it cannot corrupt the measurement. Putting it in
the evaluation stage was the obvious choice and the wrong one: an approach
adjusted in response to the held-out set has been tuned on that set, and nothing
downstream can falsify anything afterwards.

So the two are separate stages over one corpus, split 80:20:

``tune``
   Runs **train + validate** (80%) in a private worktree. Measures, and when
   instances fail, refines — ``research_refine_approach``, apply, re-measure,
   up to ``MAX_REFINEMENTS``. Failing here refutes nothing: train is where
   approaches are discovered and validate is where they are tuned, so a failure
   is unfinished work.

``evaluate``
   Runs **test** (20%) once, on whatever tuning left behind, and may change
   nothing. ``final_revision`` resolves the refinement lineage so the score
   lands on the version tuning produced rather than the one it started from —
   otherwise the improvement is measured away and the stage is worthless while
   appearing to work.

``MIN_CORPUS_INSTANCES`` is 20, and ``split`` warns below it. At twenty the
unseen set is four cases; at ten it is two, and two cases can be passed by
accident — which then reads as ``confirmed`` and licenses writing the approach
up as knowledge. The corpus must also be diverse across the declared axes,
negative cases included: a change that ignores everything passes every positive
case there is.

An approach IS a pipeline
-------------------------

An approach is a *way of solving the problem*, and the honest expression of a
way is a sequence of steps. Recorded as a name and a paragraph, it can only be
argued about; recorded as a pipeline it can be run, measured, refined and — if
it wins — shipped.

So the flow carries pipelines rather than descriptions:

* ``propose`` records each candidate with ``research_record_pipeline``;
* ``tune`` runs those steps to measure the approach, and re-records the pipeline
  it actually executed — the one stage that knows the steps are real rather than
  imagined;
* ``evaluate`` scores the pipeline against held-out data;
* ``execution-plan`` calls ``research_adopt_pipeline``, promoting the winner's
  own steps to be the plan, and builds a capability for every deterministic
  step **across every live approach** — not only the winner's.

That last point is what makes the fallbacks real. The alternates are the path a
retry takes, and a fallback whose steps have no tools is prose the next attempt
must interpret at the exact moment the cheap answer has already failed. The
skill therefore carries the leading pipeline in full and the next three as one
line per step, ranked by the same metric — compact by construction, because four
pipelines in full would exceed the block limit and be rejected, which is how a
fallback silently stops existing.

Adopting rather than rewriting matters for the same reason the figure of merit
is fixed in advance: a plan written fresh at the end of research is a fourth
version of something already established three times, and it is the version
nobody measured.

The solution is a sequence of steps, and each step wants to be a tool
---------------------------------------------------------------------

What research delivers is a **method**, not an answer. A diff solves one
instance; a skill is filed under a subject and has to solve the next one too.
So ``research_write_plan`` records the ordered steps that solve this *class* of
problem — "find every place the value is compared against the pattern", not
"edit line 604" — and the playbook renders them into the skill as a numbered
pipeline.

Each step is tagged, and the tag decides what it becomes:

``deterministic``
   Same inputs, same outputs, every time. It gets a capability built for it with
   ``capability_new`` and appears in the skill as ``tool_name(...)`` — the next
   attempt calls it. Locating call sites, normalising a path, running the
   corpus: these are tools, and each one built is work no future attempt pays
   for again.

``judgement``
   A real decision that needs a model. Kept few and labelled as such, so a step
   that needs a person is never mistaken for infrastructure nobody built.

Measured, the first time an attempt ran a plan built this way:

.. code-block:: text

   skill_load(pylint-dev)
   verify_recursive_ignore_paths(.)        reproduce
   apply_ignore_paths_recursive_fix(.)     apply
   verify_recursive_ignore_paths(.)        confirm
   run_ignore_paths_regression_tests(.)    regressions

**7 steps, 1,136 generated tokens.** The same task, two runs earlier, following
prose: 51 steps and 3.2M cache-read tokens.

The preference for tools is economic, not aesthetic. A capability costs one tool
call and behaves identically forever; an instruction is read, interpreted and
acted on afresh by every task that loads the skill. Measured on pylint-7080: an
attempt following prose reached the correct edit in six steps and spent
forty-five more around it, at ~54k tokens of working context per step. The
corrector enforces the split — a deterministic step with no capability fails
``invariants`` as ``N deterministic step(s) have no capability``, because a plan
that reads as automated while every attempt still does the work by hand is the
failure this distinction exists to catch.

The measured change travels as evidence
---------------------------------------

The point of researching before an attempt is that the attempt becomes cheap.
It was not: research would reach the right answer and the attempt would then
rebuild it. Measured on pylint-7080 — the skill directed the correct edit in six
steps, and the attempt spent forty-five more around it at ~54k tokens of working
context per step. Re-deriving what research already made is the largest
avoidable cost in a researched attempt.

The tuning stage already produces the artefact: a candidate applied in a private
worktree and run against the corpus. That worktree was then discarded. Now the
harness captures ``git diff`` from it and ``record_change`` writes it to
``research/changes/<topic>-<key>.patch``, referenced from the approach as
``change_patch`` with ``change_files`` and ``change_lines`` describing its shape.

It is evidence, not the method: proof the approach was really applied and
measured, and a reference when a step turns out ambiguous. The attempt is
pointed at the steps, never told to replay a diff.

**A file, not an inline field.** Inlining a 4 KB patch would put it in the
approach, in the skill, in every quote of the skill and in every subsequent turn
of the conversation — paying for the change repeatedly in order to avoid
deriving it once. As a path it costs nothing: the playbook marks the candidate
**patch on file**, the attempt runs ``git apply`` and goes straight to
verifying, and the diff never enters anyone's context.

Captured by the harness rather than written out by an agent, so what the attempt
applies is the change that was *measured* and not a description of it that may
differ in exactly the detail that mattered. ``CHANGE_LIMIT`` (4000 characters)
refuses anything larger: a diff that big is a working tree with debris in it
rather than a fix.

The solution is fetched a block at a time
-----------------------------------------

The skill an attempt loads is re-read on every step it takes: each api call
carries the whole conversation again, so a block loaded once and never used
costs its tokens once per *step*, and these attempts run to dozens. Measured: a
working context of ~54k re-read 72 times came to 4.3M cache-read tokens against
23.7k actually generated.

So the attempt does not load the solution skill whole. It queries the knowledge
graph for the block it needs and fetches that section:

.. code-block:: text

   graph_query(question="steps to solve <topic>")   locate
   graph_get_node(node=...)                         fetch that section only

A heading node resolves to exactly its markdown section, so ``Steps to solve X``
comes back without the evaluation notes, the fallbacks, the aspects
investigated, or everything tried and refuted — all of which the skill also
holds, and none of which is needed to start. The fallback block is fetched the
same way, and only when the leading approach has actually failed.

``execution-plan`` calls ``graph_ensure`` immediately after writing the skill,
because that is the moment it changed; without it the first query pays for a
rebuild or misses the block entirely. ``skill_load`` remains as a fallback, and
an attempt that needs it is told to say so — a graph miss is a defect worth
knowing about rather than a silent doubling of context.

A retry repairs in parallel, then reconciles
--------------------------------------------

A retry has the same shape as a research pass because it has the same problem:
several agents work in parallel on separate approaches, and what each learns
about the failing case bears on the others.

``diagnose``
   Reproduce the failure as a deterministic case, add it to the corpus as a
   held-out instance, and refine every live approach the case defeats — that set
   of revisions *is* the repair plan.

``tune`` ×N (parallel)
   One agent per revision, each in its own worktree, working on a pipeline that
   already exists against a corpus that already exists.

``collect`` (barrier)
   Reconcile. Did the repairs converge — two agents making the same change for
   the same reason is evidence about the *cause*, not coincidence. Did any
   contradict another. Does any now cover a case another still misses.

``evaluate`` ×N (parallel)
   Score on the held-out set, changing nothing.

The barrier is the point: fusing tune into evaluate here would score each
revision before anybody had reconciled what the repairs found, and the case that
defeated the last attempt is precisely what every candidate now has to answer.
Nothing is re-explored — no survey, no aspects, no fresh proposals — because
that is the expensive half of research and a retry already has its results.

A retry diagnoses; it does not research again
---------------------------------------------

The revision pass before a retry used to re-run ``propose`` — the whole
candidate space, a second time. So a pass holding a specific failure output
spent its budget re-deriving alternatives instead of reading the one piece of
evidence the first pass did not have. Measured: an attempt failed by a missing
path normalisation, and the revision answered with four fresh candidates rather
than the one-line fix to the approach that had everything else right.

Retries now run a ``diagnose`` stage instead, and it is must-finish. Its order
matters:

1. **Build the failing case first**, as a script, in a fixed scratch location.
   It must fail *the way the recorded output says* against the current checkout.
   A reproduction that passes means the reading of the failure is wrong, and
   everything built on it will be too.
2. **Classify**: did the change engage? Right-and-incomplete goes to
   ``research_refine_approach``; wrong-idea goes to a genuinely different
   candidate.
3. **Leave the test behind.** The reproduction path is recorded with the
   revision, and the attempt prompt tells the next attempt to run it: it must
   fail before the change and pass after, and the attempt may not report done
   while it still fails.

The reproduction is the part that makes this a corrector rather than a note. The
failed attempt had its own reproduction and it *passed* — the case it built was
easier than the case it was judged on, which is precisely how it shipped a fix
that did not work. Encountering a different problem on the next attempt is a
fine outcome. Failing the same way twice is the one that is ruled out.

The plan, split by determinism
------------------------------

``research_write_plan`` requires every step tagged ``deterministic`` or
``judgement``. Deterministic steps become capabilities; judgement steps become
skill blocks. An untagged step is rejected rather than defaulted — defaulting to
judgement turns mechanical work into prose that drifts, and defaulting to
deterministic promises a repeatability the step cannot deliver.

``research_verify`` is the corrector, with an extra facet beyond the standard
five:

``evidence``
   Fails when no approach records where it came from, and fails when *every*
   approach came from reading the local checkout. A set of approaches derived
   entirely from the file in front of you is not research; it is one guess
   written several ways, and in the record it is indistinguishable from genuine
   investigation.


Agents
======

Agents are defined once in harness-neutral YAML and rendered per harness:

==========  ==========================================
harness     rendered to
==========  ==========================================
claude      ``.claude/agents/<name>.md``
opencode    ``.opencode/agents/<name>.md``
copilot     ``.github/agents/<name>.agent.md``
codex       ``.codex/agents/<name>.toml``
==========  ==========================================

An agent declares a **capability level** (``level_1``–``level_4``), never a model
id. The indirection is what lets one definition run on four harnesses and makes
a model upgrade a one-line edit in ``workspace/models.yaml`` rather than a sweep
through every template.

The shipped agents:

==============================  ==============================================
agent                           role
==============================  ==============================================
``phronix-router``              entry point; scopes skills and tools per task
``phronix-researcher``          works out how an uncovered task should be done
``phronix-healer``              diagnoses and fixes, then records what it learned
``phronix-learner``             turns a finished session into durable knowledge
``phronix-verifier``            builds and runs correctors
``phronix-capability-builder``  turns procedures into MCP tools
``phronix-planner``             decomposes work
``phronix-privacy-guard``       keeps shared knowledge free of identifying detail
==============================  ==============================================

Tool lists are allowlists (``'*': deny`` plus named tools). This is right for
delegated specialists and decides what a *primary* agent can do at all — the
router has no ``Bash``/``Edit``/``Write``, so launching it as primary cannot
change a line of code.


Complexity: choosing the model level
====================================

As skills and agents grow, the work an agent does changes, and the model it
needs changes with it. ``complexity_assess`` scores an agent from its own
definition:

============================  ======  ====================================
signal                        weight  direction
============================  ======  ====================================
``reasoning_demand``          +0.30   rules and instructions to weigh
``failure_surface``           +0.25   recorded ways it goes wrong
``unverified_fraction``       +0.20   claims with no corrector
``integration_breadth``       +0.15   systems it must touch
``instruction_load``          +0.10   how much it must hold at once
``tool_coverage``             −0.25   deterministic tools *reduce* difficulty
============================  ======  ====================================

The negative weight is the point: work done by an MCP tool is work the model no
longer has to reason through, so building capabilities should *lower* the level
an agent needs. Bands map the score to ``level_1``–``level_3`` (0.25/0.45/0.70),
with a declared ``intrinsic`` floor for agents whose job is inherently hard
regardless of tooling.


Two kinds of capability, and no duplicates
------------------------------------------

Capabilities come from two places and are treated differently.

**Solution tools** are the deterministic steps of a pipeline —
``apply_ignore_paths_fix``, ``run_recursive_discovery``. They are task-shaped by
design, built by ``execution-plan`` for every live approach rather than only the
winner's, because the fallbacks are the path a retry takes and a fallback whose
steps have no tools is prose to interpret at exactly the moment the cheap answer
has already failed.

**Method tools** carry the ``probe_`` prefix and know nothing about any task:
set a fixture up in a given shape, run one area's tests and parse what failed,
apply a candidate and report the figure of merit. They are built at the *end* of
a research pass, when it knows which steps it actually repeated — building them
mid-investigation interrupts the investigation, and before the pass ends a
"reusable" tool is a guess.

The prefix decides what a ``--fresh`` run inherits. Fresh withholds what earlier
runs *learned*, not what they *built*: skills, research and solution tools stay
behind, ``probe_`` tools come through. Excluding them would make "from scratch"
mean "without tools", which is a claim about tooling rather than about learning,
and would leave every run re-deriving the same shell scripting. A prefix rather
than a metadata field because it is visible everywhere it matters — in the tool
list the agent sees, in the file name, and in the seeding decision — so a
capability that quietly encoded a task's answer under it would be visible in
review for the same reason.

**Neither kind may be built twice.** Because solution tools are task-shaped, a
step in one task's pipeline is often a step in another's, authored under a
different name by a pass that could not see the first. ``capability_new``
fingerprints the module with docstrings, comments and the tool's own name
stripped, so two versions differing only in naming and prose collapse to one
value, and refuses a duplicate — returning the existing name to use instead.
Three copies of one procedure have to be maintained, verified and chosen
between, and choosing is a decision nobody meant to hand the next attempt.

Privacy
=======

Everything phronix persists is committed and shared, so redaction happens on the
write path, not as a later audit: usernames, home paths, hostnames, emails, job
ids. ``privacy_scan`` verifies deterministically, and ``privacy_add_pattern``
teaches the redactor a leak class it does not know.

Fixtures that must contain a realistic identifier carry an explicit exemption
marker, so "this file is allowed to look like a leak" is a recorded decision
rather than an exception in the scanner.

Redaction is for the boundary, not for the local store
------------------------------------------------------

``PHRONIX_PRIVACY=off`` records text exactly as it is. The default is on, and
the upstream gate does not read the flag at all: ``phronix contribute`` scans
with ``find_identifiers``, which builds its own substitution list, so promotion
still blocks on an identifier whatever the local setting.

The distinction earns its place because a skill records *operational paths*, not
only prose. Rewriting ``/p/lustre3/<user>/...`` to ``$SCRATCH_ROOT`` turns "read
the task history at ``<path>``" into an instruction that cannot resolve — and an
agent handed one created a directory of that literal name and mirrored an old
run into it. Sixty carried files held such paths before this was found. Redact
when knowledge leaves the machine; record it faithfully while it is still here.


Profiling
=========

OTLP-shaped telemetry with an MLflow sink: a parent run per session, a nested
run per step, tokens and model level per step. The purpose is answering "what
did this cost, and where" with measurements rather than impressions.


The MCP surface
===============

84 tools across 16 services. ``context_service`` is registered first
deliberately — tool order influences what a model reaches for, and retrieval
should be the first thing it sees.

Learned capabilities are not in this table: past ``DISPATCH_THRESHOLD`` they
are reached through ``capability_call`` rather than registered individually.
See *Capabilities*.

=====================  ==========================================================
service                tools
=====================  ==========================================================
context                ``context_skills`` / ``context_memory`` / ``context_for_task``
skills                 ``skill_list`` / ``skill_index`` / ``skill_search`` /
                       ``skill_load`` / ``skill_create`` / ``skill_write`` /
                       ``skill_write_lesson``
authoring              ``skill_define`` / ``agent_define`` (declarative, idempotent)
memory                 ``memory_list`` / ``memory_recall`` / ``memory_read`` /
                       ``memory_write``
graph                  ``graph_ensure`` / ``graph_query`` / ``graph_get_node``
conversation           ``conversation_outline`` / ``conversation_search`` /
                       ``conversation_turn`` — what THIS session already
                       established, so a stage does not re-derive it
research               32 tools. Beyond the gate-and-strategy set
                       (``research_assess`` / ``research_prior`` /
                       ``research_define_fom`` / ``research_add_approach`` /
                       ``research_choose`` / ``research_write_plan``) there are
                       the corpus tools (``research_declare_corpus`` /
                       ``research_split`` / ``research_add_instance(s)`` /
                       ``research_coverage``), the trial record
                       (``research_record_trial`` / ``research_evaluate_approach``
                       / ``research_ruled_out`` / ``research_dead_approaches`` /
                       ``research_mark_working``), the pipeline form
                       (``research_record_pipeline`` / ``research_adopt_pipeline``
                       / ``research_record_step_reached``), the aspect set
                       (``research_set_aspects`` / ``research_add_aspects``), and
                       the running record (``research_observe`` /
                       ``research_notice`` / ``research_status``)
solution               ``solution_check`` / ``solution_repair`` — the filing
                       checks are RUN rather than requested, and a mechanical
                       fault is repaired rather than only named
schema                 ``research_validate`` — the research record's schema,
                       not just its location
layout                 ``layout_check`` — where a skill's files belong
privacy                ``privacy_scan`` / ``privacy_redact`` /
                       ``privacy_suspects`` / ``privacy_add_pattern``
capability             ``capability_list`` / ``capability_new`` /
                       ``capability_session``
verification           ``verify_list`` / ``verify_run`` / ``verify_coverage`` /
                       ``verify_new``
complexity             ``complexity_assess`` / ``complexity_reassess`` /
                       ``complexity_impact``
profiling              ``profile_bind`` / ``profile_step_begin`` /
                       ``profile_step_end`` / ``profile_status`` / ``profile_report``
sync                   ``agents_sync`` / ``permissions_sync`` / ``hooks_sync`` /
                       ``skills_sync`` / ``phronix_status``
=====================  ==========================================================

Deployment
==========

``phronix deploy`` is idempotent and reversible. It creates the project layer,
inserts a *marked block* into ``CLAUDE.md`` / ``AGENTS.md`` /
``.github/copilot-instructions.md`` rather than overwriting them, repoints Claude
Code's per-project memory at the committed store, and adds rendered artefacts to
``.gitignore``. Anything that would destroy existing content reports ``conflict``
and does nothing.

``phronix deploy --check`` diffs against a scratch deployment and reports what
would change, without touching the tree.


The benchmark
=============

phronix claims agents improve with use. That claim is worth only as much as the
measurement behind it, so the benchmark lives in ``tests/benchmark/`` and is
built to be able to *disconfirm* the claim.

Arms
----

===========================  =========================================
arm                          what it is
===========================  =========================================
``mini``                     mini-swe-agent, the reference
``opencode-bare``            opencode with no phronix — the baseline
``opencode-phronix-frozen``  full scaffolding, store mounted read-only
``opencode-phronix``         full scaffolding, store read-write
===========================  =========================================

The frozen arm is the control: identical scaffolding, identical tools,
``:ro`` at the mount. ``bare → frozen`` is the cost of the scaffold;
``frozen → learning`` is the claim. Read-only at the mount rather than by
convention, because an arm that *could* write is not a control.

Per-task flow
-------------

1. **research** (before attempt 1; a *diagnose* pass before each retry)
2. **candidates** built in parallel, one agent each, own container and checkout
3. **evaluate** each patch in a pristine container
4. **record** locations and scores into the ledger — by the harness, not by an
   agent, since both are facts on disk
5. **learn** with the verdict in hand
6. **retry**, which must not re-edit a falsified location without new evidence

Fairness rules
--------------

* **Identical prompts**, except scaffolding the arm genuinely deploys.
* **Test feedback goes to every arm**: the failure output is the task's own
  product, not something phronix brings. What differs is *memory* — phronix
  distils it into a stored lesson that survives into later tasks; the baseline
  gets it in-context and loses it.
* **The reference patch and the test patch never reach an agent.** Maintainer
  hints and grading-test names are available behind ``--with-hints`` and
  ``--reveal-target-tests``, both off by default, both printed loudly and
  recorded in the manifest, because published SWE-bench numbers exclude them.

Failures that end the run
-------------------------

Most things that go wrong are results: a task fails, a patch regresses, an
approach is refuted. Two are not, and both share a shape — every row produced
after them *looks like a result*, so the run keeps reporting numbers that mean
nothing.

``ResearchCollapsed``
   A phronix research pass produced no tool calls at all. The agent never
   started — bad command, dead endpoint, missing binary — and the arm silently
   degrades into a plain agent with extra scaffolding while every number it
   produces is attributed to phronix.

``EnvironmentGone``
   Two consecutive tasks could not get a container. Measured: a flux allocation
   hit its 24h wall limit mid-run, and each remaining task spent two attempts
   rediscovering it. The rows read ``fail``, 0 steps, 0 tokens — and one of them
   held a real patch that was simply never judged, which is worse than a missing
   row because it reads as a measured failure of the arm.

One task without a container is bad luck; two in a row is the host. Neither
exception is swallowed by the per-attempt handler ("a crashed attempt is data")
or the per-arm one ("one arm failing must not void the others").

The test runner must exist before anything means anything
---------------------------------------------------------

Three faults made whole instances unjudgeable while looking like bad patches:

* **No pytest in the image.** sympy's testbed environments ship without it, so
  every test scored not-passed. Now installed into the *container* — never the
  host venv, because the instance pins the dependency versions its tests are
  written against — from a wheelhouse mounted at ``/wheels``, so scoring a test
  never depends on the network.
* **Ids that cannot match.** SWE-bench stores sympy's ids as bare function
  names while pytest prints full node ids, so every sympy instance scored 0 of
  30 on tests that had just printed ``PASSED``.
* **Fixtures handed to pytest as tests.** flask-4992's test patch adds
  ``tests/static/config.toml``; pytest given a data file collects nothing at
  all. Test files now come from the test patch, filtered to test modules.

A run producing no per-test outcome at all is a ``runner_failed`` verdict, not a
score: no patch can make the tests fail to *run*. It is not cached as
pre-existing breakage and it does not consume retries.

``phronix-bench baseline`` runs every task's tests unpatched — no agent, no
tokens — and reports what the environment does. It caught all three above, and
it is cheap enough to run before any unfamiliar task list.

Pre-existing failures
---------------------

SWE-bench assumes the instance image reproduces the original environment so that
every ``PASS_TO_PASS`` test passes before the fix. That assumption does not
always hold. Measured here: ``pylint-7080``'s ``test_stdin[/mymodule.py]`` fails
at base commit, and two ``toml_config`` tests fail on a ``tomlkit`` version skew.

Since ``resolved`` requires all ``PASS_TO_PASS`` to pass, one pre-existing
failure made the instance **unresolvable by any patch, including the official
one** — an agent produced the upstream fix byte for byte and scored ``fail``.

So the harness measures the unpatched repository once per instance, caches it,
and discounts already-broken tests, reporting them as ``pre_existing_failures``.
Never silently: an unexplained exclusion is how a benchmark starts flattering
itself.

Metrics
-------

``tries``
   attempts until pass, and steps per attempt.
``learning rate``
   two numbers, because either alone misleads: the OLS slope of ``resolved``
   against task index *and* the reuse rate — the fraction of tasks retrieving a
   skill an **earlier** task wrote. A positive slope with zero reuse is ordering
   luck, not learning, and the report says so.
``tokens``
   measured from the harness's event stream, including the research and
   learning passes. Hiding those would make phronix look cheaper than it is.
``time and cost``
   split three ways per attempt — solving, research, learning — because
   research runs *inside* the attempt's wall clock (it needs the exported
   checkout) and the combined number reported a six-step attempt as taking
   seventeen minutes when sixteen of them were research. The baseline it is
   compared against has neither, so only the solve figure is comparable.
   Reported as ``solve_s`` / ``research_s`` and ``cost_usd`` /
   ``research_cost_usd``: "phronix costs more" and "phronix's *research* costs
   more" are different claims, and only the split can tell them apart.

Verdicts are deliberately conservative: ``learning_demonstrated``,
``learning_suggested``, ``improvement_unexplained``, ``no_learning``,
``uncontrolled``, ``no_data``.

Observability
-------------

Each arm writes ``trace.log`` (human, tail-able) and ``trace.jsonl``. It records
every phronix tool call *and every rejected one*, the research record after each
pass, what each attempt changed and scored, whether an attempt was **better or
worse** than the previous one, and what reached the store by block title.

This exists because of a specific failure: a run reported plausible results for
hours while the phronix arm called no phronix tools at all, and no summary could
have shown it. That detector counts tool calls in **both** harnesses' stream
shapes — opencode's flat ``part.tool`` and Claude Code's ``tool_use`` blocks
nested in an assistant message. Reading only the first meant every Claude
research pass reported zero calls while its trace showed a dozen, so the alarm
for research that never ran was firing on healthy passes and would have been
invisible on a real one.


Design rules that earned their place
====================================

Each of these was learned by being violated.

**Probe by doing.** ``can_store_images`` pulls a real image rather than checking
filesystem type or xattr support — every cheaper proxy was either wrong or
right-for-the-wrong-reason, which is worse because it looks authoritative.

**A near-miss must not discard knowledge.** ``skill_write(kind="lesson")`` is
routed to LESSONS.md, not rejected. The old error message named the correct tool
— the call knew where the content belonged and refused to put it there — and a
run's only piece of learning was lost to it.

**A failing corrector is a verdict, not a puzzle.** When a verifier fails after
a change, the attempt has two doors and prose is not one of them: revise the
change, or — with concrete evidence the check itself is wrong — fix it with
``verify_new`` and record why with ``skill_write_lesson``. Measured: an attempt
made the correct edit in six steps, its verifier failed on a path with a leading
``./``, and it spent forty more steps establishing that the fix "works when
targeting ``src`` directly" — rediscovering the verifier's point and dismissing
it. The task then failed on exactly that case, ~3M cache-read tokens later, and
nothing was healed or recorded because neither was reachable from where the
agent stood.

**Report the reason, not just the outcome.** The evaluator runs with
``--tb=short`` and extracts the failure detail, because "which test failed"
without "why" turns a retry into a re-roll of the same dice.

**Reporting must never break the run.** Every tracer method is wrapped: a
formatting bug once raised through the attempt loop and recorded two attempts as
``0 steps, 0 tokens``, which reads exactly like an agent that ran and did
nothing.

**One definition per decision.** ``choose`` and the corrector share one ranking
function; when they had separate ones, the corrector failed choices that were
correct under the chooser's own rule.

**Fail fast when the environment is gone.** A preflight check refuses to start
against an unreachable container host, and repeated isolation failures end a
task. An expired allocation once produced six tasks of empty results that looked
like agent failures.


Running the benchmark on a local GPU fleet
==========================================

The comparison needs thousands of agent turns against an identical model, which
rules out a metered API. The fleet is eight nodes of an MI300A machine serving
one open-weight model, with everything below chosen against a measurement
rather than a default.

The machine and what it forces
------------------------------

Each MI300A APU has 128 GB of unified HBM and there are four per node, so eight
nodes give 32 independent model servers. Three properties of the environment
shape the deployment more than the GPUs do:

* **Lustre cannot host container storage.** It has no user extended attributes,
  so an overlay backend fails ``lsetxattr /boot`` and a vfs backend fails
  ``pivot_root`` on permissions. Podman's image store must live on the
  node-local SSD (``/l/ssd``, 200 GB xfs). ``/tmp`` is not an alternative — it
  is tmpfs, and therefore RAM.
* **Model weights must be node-local too.** Sixty-odd GB of MXFP4 read from
  Lustre by 32 servers at once is a self-inflicted denial of service. Weights
  are staged once to each node's SSD with ``dcp`` (mpifileutils) and loaded from
  there.
* **The kernel keyring is a quota.** 200 keys per user, about two per container.
  Leaked containers exhaust it and the *next* run fails at startup with an error
  that says nothing about keys; the kill path prunes containers for this reason.

``dcp`` assumes a **shared** destination and splits work by rank, so a single
job spanning nodes writes a *fraction* of the file to each — measured as 7.9,
15.9 and 23.8 GB of one 60 GB file. Staging therefore runs one
``flux run -N1 -n 64 --requires=host:<node>`` per node, in parallel.

Context is a pool, not a per-slot figure
----------------------------------------

``llama-server``'s ``-c`` is **divided** by ``--parallel``. ``--parallel 16 -c
524288`` gives each slot 32 768 tokens, and an agent that exceeds it gets
``"reason": "length"`` — which the harness reports as *agent produced no patch*.
An entire run failed that way with nothing in the trace naming the cause.

Asking for more than the model was trained on is worse than asking for less:
``n_ctx_seq`` above ``n_ctx_train`` triggers RoPE scaling, which rescales
positions for **every** request on that server, not only the long one. The
``agent`` profile is therefore ``--parallel 4 -c 524288`` — four slots of
131 072, exactly ``n_ctx_train``.

Prefill dominates, so cache affinity is the main lever
------------------------------------------------------

Measured on an idle backend with a 24 072-token prompt:

============================  ===================  ==========================
request                       prefill              note
============================  ===================  ==========================
cold                          11 092 ms            2 170 tok/s
same prompt again             17 ms                24 131 tokens cached
============================  ===================  ==========================

A factor of 74, and it applies to every turn of every agent, because an agent's
context is mostly the same prefix as its previous turn. Decode by comparison is
76 tok/s single-stream and is a property of the hardware.

The prompt cache is **per server**. A gateway that load-balances by least-busy
therefore destroys the thing that matters most: consecutive turns of one agent
land on different backends and each pays full prefill. The gateway consequently
publishes a per-backend alias (``<model>@<n>``) alongside the shared name, and
each task is pinned to one alias by a hash of its instance id — spreading load
across backends while keeping any one agent's turns on the backend that already
holds its prefix.

Claude Code accepts the ``@n`` form; the ``unrecognized_model`` warning it emits
is from a background session-title call and does not affect the run.

Pinning alone was not enough, because the cache is per **slot**, not per
server. A backend running four slots holds four unrelated conversations, and
each arriving request evicts whichever prefix it displaces — so an agent
returning for its next turn finds its own prefix gone and pays full prefill
again, on the very backend that was supposed to be holding it. Measured under
four slots: 2 314 160 prompt tokens against 33 441 generated, prefill 77% of
GPU time.

The ``solo`` profile gives each GPU a single slot. One slot holds one
conversation, so nothing else can evict it, and the whole 131 072 window
belongs to that conversation without dividing a pool. The capacity surrendered
is nominal: it trades 128 concurrent requests for 32 on a fleet that had been
running 3–22 in flight with most backends idle.

That change has a sharp edge. A task's pin keeps its own turns together, but a
research fanout is eight *separate* conversations, and sending them all to the
task's single backend serialises them — harmless at four slots, fatal at one.
Fanouts therefore walk outward from the task's own pin, one backend per
position, so agents spread while each agent's turns stay put. What is pinned is
a conversation, not a task.

The same correction applies to the two arms of one task. They were given a
shared backend on the reasoning that they would share a warm prefix; they share
none, because the bare and phronix arms send different system prompts and
diverge from the first token. The pin key is therefore ``arm:instance``.

Measured across the change, same six tasks:

========================================  ============  ============
                                          4 slots       1 slot
========================================  ============  ============
prompt tokens per generated token         69            6
prefill share of GPU time                 77%           60%
aggregate fleet decode                    2 844 tok/s   3 306 tok/s
tasks resolved                            1 of 6        2 of 5
========================================  ============  ============

One slot then reveals the next constraint rather than ending the story: 32
concurrent requests for a workload of two arms times six tasks times an
eight-wide fanout, observed as 9 requests in flight and 31 queued with 23
backends idle. Per-agent action rate reads unchanged at 0.30/s because queue
time is time between actions.

Two slots is the response, and it is not a return to the old failure. What made
four slots harmful was eviction *destroying* a prefix; ``--cache-ram`` now parks
the evicted conversation instead, so eviction costs a memory copy rather than
eleven seconds of re-prefill. The protection that was missing then exists now,
which is why the same nominal setting has a different meaning.

What "throughput" means here
----------------------------

A benchmark task is the wrong unit: one task is minutes of an agent reading
files and running commands, and a run that has finished no tasks yet may be
working hard or barely moving. The unit that answers the question is an **agent
action** — one tool call, or one completed model turn — and the run-wide rate
factors into two numbers that have different fixes:

.. code-block:: text

   actions/s (run)  =  actions/s per agent  x  agents in flight

A low per-agent rate is a model or harness problem. A low agent count is a
concurrency problem. Reporting only the product cannot distinguish them, and
they were confused for hours.

Two counting details matter. Turns are deduplicated **by message id**, because
a streamed assistant message arrives as several events sharing one id and
counting events overstated turns by 35%. Per-agent time comes from the
transcript's own timestamps, not the file's: on Lustre ``st_ctime`` moves on
every append, so ``mtime - ctime`` is ~0 and the per-agent rate silently
vanishes.

What was actually slowing it down
---------------------------------

Measured before and after, same six tasks, same fleet:

======================  =====================  =====================
                        before                 after
======================  =====================  =====================
per agent               0.30 action/s          0.76 action/s
                        (one every 3.3 s)      (one every 1.3 s)
fleet in flight         3–5 requests           22 requests
======================  =====================  =====================

Three causes, in order of what they cost:

* **A start throttle written for a different backend.**
  ``llm.min_seconds_between_starts: 1.5`` exists to stop a wide fanout burning
  a metered Anthropic allocation in minutes. On a local fleet there is nothing
  to meter, and the same 1.5 s is pure serialisation: an eight-way fanout paid
  12 s of dead time before its last member started, every stage, every task.
* **Fanout caps chosen when the fleet was one server.** Aspects and approach
  evaluations are fused fanouts — the phase costs its slowest member whether
  there are three or eight — so a cap of 5 and 3 bought nothing and left 28 of
  32 backends idle. Now 8 and 6.
* **Logging was suspected and cleared.** Two appends per event, against roughly
  one event per action; at 1.3 s per action it is not the bottleneck. Worth
  recording because it was the intuitive answer and it was wrong.

Arms already ran concurrently by default; ``--serial-arms`` is the opt-out, and
is required only where two arms would contend for one node's containers.

A task unit occupies about **0.53 slots** — much of its life is spent checking
out repositories, running tests and evaluating patches rather than talking to
the model. Sampled against a live 12-unit run: 2, 9, 8, 7, 6 requests in
flight. Tasks needed to fill a fleet is therefore ``capacity / (0.53 x arms)``,
which is what ``--fill-fleet`` computes.

Where the agents run
--------------------

The agents run on the **allocated compute nodes**, not on the machine driving
the run. This is recent and it was not a tuning change: measured at twelve
tasks, the driving host — a shared login node — carried 60 ``claude`` processes
at load 10.8 on 48 cores while every allocated compute node sat at 0.00. The
allocation was being used for containers and for nothing else, and the ceiling
on parallelism was a machine outside it that seventeen other people were also
using.

Each task's agents are placed on the node that already holds its container, so
its reasoning and its test runs share a host, a page cache and a checkout. The
invocation travels as a generated script on the shared filesystem rather than
an ssh command line, because the environment is dozens of variables including
paths with spaces, and every one would otherwise survive two levels of shell
splitting.

Two properties of that environment are not optional:

* **Only names a shell can export.** Lmod publishes ``module`` and ``ml`` as
  ``BASH_FUNC_module%%``, whose values are multi-line function bodies. Those
  are not valid identifiers, so the ``export`` fails — and the body then runs
  on past the failed line, so the shell reads ``case "$-" in`` and the rest of
  the function as commands. The script is corrupt from that point. Every
  recording stage produced nothing and no output at all until this was
  filtered.
* **Per-task state must be thread-local.** One ``Arm`` object serves every task
  that arm runs, concurrently. A per-task value written onto it as a plain
  attribute is a data race whose result looks plausible: the last task to start
  overwrites it for all the others. Measured on the first placement attempt, 25
  agents landed on one node of five and fifteen stayed local. The model pin had
  the same race silently, sending tasks to each other's backend and destroying
  the prompt-cache locality the pinning exists to create.

Fanned-out stages inherit the placement explicitly. A worker thread starts with
empty thread-locals, so research — which fans out through six pools — ran every
one of its agents on the driving host while the attempt was correctly placed.

Per-agent decode is the number that decides
-------------------------------------------

Concurrency is not throughput. What decides whether an attempt finishes inside
its budget is how fast **one** agent decodes, which is the replica's rate
divided by the requests sharing it:

======================  ==============  ==============
shape                   per replica     per agent
======================  ==============  ==============
12 replicas x 4 slots   26 tok/s        7 tok/s
20 replicas x 2 slots   26 tok/s        13.5 tok/s
======================  ==============  ==============

At 7 tok/s a twenty-turn attempt cannot finish in 1800 s, and sixty task-arms
ran eighteen minutes with zero completions — not stuck, each crawling. More
slots buy concurrency by dividing each agent's share, and an attempt that
decodes too slowly produces nothing at all. So the fleet is sized for roughly
**one concurrent request per replica**, and task parallelism follows from that
rather than from the node count.

The same arithmetic sets ``--parallel``: a task occupies about 0.53 slots and
runs two arms, so 120 tasks against 256 replicas is approximately one each.

Images come from the filesystem, not the registry
-------------------------------------------------

Container startup resolves an image **cache, then PFS archive, then registry**
— in that order, with the registry last.

Pulling first is the obvious implementation and it fails at scale. Every image
is archived on the PFS by ``prefetch``, and the node-local podman store is a
cache that a freshly scheduled node does not have. A group landing on new nodes
therefore went to Docker Hub for thirty images at once, and Docker Hub rate
limits unauthenticated pulls:

.. code-block:: text

    toomanyrequests: You have reached your unauthenticated pull rate limit

That failed **all sixty task-arms of a group inside four minutes**, reported as
``isolation: could not start <image>`` — which reads as a missing or broken
image rather than as a quota. The archives were on the same filesystem the
whole time.

The benchmark's own environment is read-only
--------------------------------------------

The tasks *are* Python repositories, and an agent reproducing a bug installs
the repository it is working on. It inherits the harness's environment, so
``pip install -e .`` rewrote the harness's own ``site-packages``: seven
SWE-bench repositories were editable-installed there, ``pytest`` was replaced by
a task's 4.6.1 checkout and ``pluggy`` dragged to 0.13.1, and the benchmark's
test suite could no longer start. One ``.pth`` pointed into the **previous
day's** run, so it had been changing what every later task imported, silently,
across runs.

Two softer guards leak and should not be trusted. Dropping ``VIRTUAL_ENV`` and
the venv from ``PATH`` is undone by the same function that puts node there; a
``pip`` shim earlier on ``PATH`` never sees ``python -m pip`` or an absolute
``bin/pip``. A read-only ``site-packages`` does not care how pip is spelled, the
harness only reads at runtime, and an agent's install fails naming the
directory.

Surviving the machine
---------------------

A 64-node job meets hardware failure as a matter of course, and concurrent jobs
meet each other. Both were silent before they were designed for.

**Concurrent runs must not share state.** ``deploy.sh`` writes its fleet
description to ``$RUNDIR/cluster.json`` and copies it to a shared path. That
copy is last-writer-wins, so two jobs queued behind each other would send the
first job's tasks to the **second** job's gateway: one fleet serving twice its
load, the other idle, and the manifest naming the wrong gateway so the trace
would not reveal it. Each job now owns a ``RUNDIR`` named for the job rather
than the clock, and addresses its own fleet. The task-list slice had the same
shape of bug — its path derives from ``--size`` and ``--index`` alone, so four
runs of the same 300 wrote one file at once — and is now renamed into place.

**Node failure is handled in three layers**, because it arrives in three sizes:

============================  ==================================================
failure                       response
============================  ==================================================
a task's container host       the task moves to another node and retries; the
                              try does not count toward the abort, since a try
                              that never ran on a working node is not evidence
                              about the environment. Bad hosts are recorded
                              process-wide and new tasks round-robin over the
                              survivors.
the run dies                  the batch job supervises up to four passes,
                              re-deriving which nodes still answer each time
a node dies outright          Flux kills the job; the resubmission resumes
============================  ==================================================

Resuming works because ``results.jsonl`` is written per task as it finishes —
it was always a checkpoint, and nothing read it. ``--resume auto`` finds the
newest incomplete run of the same task list and model, carries its results
forward so the report covers the whole list, and skips those tasks. It tolerates
the torn last line a killed job always leaves. Before this, a node failure cost
105 in-flight tasks *and* the ~500 task-arms the job had already finished.

Budgets are measured, and the fallback matters
----------------------------------------------

Stage budgets are calibrated against a model at roughly 1000 tok/s, so hardware
that decodes at 13.5 needs them scaled. ``budget_scale`` measures the fleet and
derives the multiplier — and its **fallback** turned out to matter more than the
measurement.

The rate is read from ``predicted_tokens_seconds``, which counts *finished*
requests, so it reads 0 on a fleet deployed seconds ago — which is every batch
run, because the job brings up the fleet and starts immediately. An unmeasurable
rate was read as "no fleet, therefore hosted", which takes the hosted scale of
0.5 and **halved every budget on the slowest hardware available**. Measured
across two 300-task runs: ``budget_scale = 0.5`` in both manifests and 778
stages killed at their ceiling, 563 of them research — the stage the next
attempt depends on, so try 2 opened with "no skill covers this task".

Two rules follow. A configured-but-unmeasured fleet is **not** hosted: it gets a
generous multiplier and is not cached, so a later caller measures once traffic
exists and the budgets correct themselves mid-run. And the tracked loop's
multiplier is **bounded** separately, because that loop is sequential — research
blocks the next attempt — so the 50x a very slow fleet computes would put one
stage at four hours and the task would never reach try 2.

Failures are classified before they are counted
-----------------------------------------------

Three kinds of failure read identically in a trace and point at completely
different work, so ``error-report.py`` separates them:

=========  =====================================================================
PIPELINE   ours: a harness bug, a moved binary, an ssh limit, a budget
TESTBED    the SWE-bench image's own environment — a repository's conftest, a
           dependency that drifted. Nothing in this repository fixes these
MODEL      the benchmark working: the agent did not solve the task
=========  =====================================================================

Anything unrecognised is reported as UNCLASSIFIED rather than assumed to be a
model failure, because a fault the report does not know about is the one worth
seeing.

The distinction has teeth. A patch that does not parse stops the tests from
running, which looks exactly like a runner that never started — and the code
assumed "a patch that breaks everything still makes the tests RUN", which is
false when the patch is not valid Python. Scoring it as a runner fault inflated
the pipeline count *and* told the attempt the runner broke rather than that its
own edit will not parse, so the next try had nothing to correct.

The ratio is the diagnostic. A healthy run is model-dominated: one 300-task run
measured 1195 model failures against 274 pipeline. A run where pipeline
outnumbers model is measuring the harness, not the model, and its numbers should
not be read as a result.

Sampling: what the model was evaluated with
-------------------------------------------

Sampling parameters are not a matter of taste; they are part of the model's
evaluation contract, and picking them by intuition changes the score being
measured.

For ``gpt-oss-120b`` the reference is **temperature 1.0, top-p 1.0, top-k
disabled**. Two traps sit either side of it: ``top_k`` defaults to 50 in
transformers and 40 in llama.cpp, so *not setting it* silently truncates the
distribution; and turning sampling off entirely (``--temp 0 --top-k 1``) is
argmax, which is not what the model was measured under either. Repetition,
presence and frequency penalties stay neutral — a reasoning model revisits its
own tokens by design, and penalising that damages exactly the traces the
benchmark cares about.

``--jinja`` is not optional. It selects the Harmony chat template, which is what
parses tool calls and separates the reasoning channel. Without it the model
emits tool calls as prose — observed directly as a hallucinated
``{"tasks": [{"type": "add_file", ...}]}`` blob in place of any real tool use.

Reasoning effort is the one genuine speed/accuracy dial, and it points the wrong
way for this benchmark: low effort is what makes the fleet fast, and the
published SWE-bench work uses medium or high, which score alike. That tension is
unresolved and is recorded as a weakness below rather than papered over.


Where the design is still weak
==============================

Stated plainly, because a design document that only lists strengths is
marketing.

* **Falsification is per-task.** An approach falsified on one instance does not
  yet stop a later task proposing the same shape elsewhere.
* **Plans skew deterministic.** Research repeatedly tags every step
  ``deterministic``, including ones that plainly need judgement — which suggests
  the tag is being applied to satisfy the corrector rather than to describe the
  work.
* **Label stability versus history-independence** cannot both hold. Stability
  was chosen; a rebuilt store can therefore allocate different labels than an
  incrementally grown one.
* **Reasoning effort is set against its own evidence.** The fleet runs
  ``gpt-oss-120b`` at low effort because that is what makes it fast, while the
  published SWE-bench reproductions use medium or high. Speed was chosen first
  and deliberately; the accuracy cost has not been measured.
* **The local model is not comparable to the hosted one.** Observed directly:
  turns that end cleanly without an edit, and tool calls emitted as prose. No
  sampling or budget setting closes a capability gap, so bare-versus-phronix
  within this fleet is sound while fleet-versus-hosted numbers are not.
* **Cost.** Research plus parallel candidates plus a learning pass is several
  agent invocations per task. It buys measured knowledge instead of guesses, but
  the trade is real and the benchmark counts every token of it.
* **An arm can report as phronix without having used it.** One 300-task run
  logged 467 stages as "used NO phronix tools" against 7 for the same code on
  another model. The framework was demonstrably working in that run — 261 tool
  calls, 175 skills written, 77 skill loads — and most of the flagged stages are
  the first attempt, where a fresh run has nothing to retrieve. The remainder is
  unexplained. Until it is, that run's phronix-versus-bare comparison is not
  evidence, and the flag cannot be read either as a fault or as noise.
* **Only one of three node-failure layers is proven.** Per-task failover,
  supervised passes and ``--resume auto`` are tested but have not yet caught a
  real node failure; the only layer confirmed in production is the image
  archive. A design that has not met the failure it was written for is a
  hypothesis.
* **The host-memory ceiling is unmeasured.** MI300A memory is unified, so four
  replicas share 128 GB per node with the co-located agents and containers. A
  node was lost mid-run with no allocation error in any server log — consistent
  with a host OOM-kill and equally consistent with a hardware fault. Nothing
  distinguishes them after the fact, and the headroom has never been measured.
