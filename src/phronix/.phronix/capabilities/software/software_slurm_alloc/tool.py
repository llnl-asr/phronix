"""software_slurm_alloc: Slurm allocation and job-step workflow (counterpart of software_flux's flux-alloc): discover partitions and per-partition MaxNodes, read sbatch --test-only start estimates, allocate with salloc/sbatch, run and co-schedule steps with srun --overlap --nodelist, keep helper daemons alive as long-lived steps, pin GPUs (--gres vs --gpus-per-task), avoid env-propagation traps, cancel only your job, make long sweeps resumable, decode squeue reasons, and verify scale with sacct. Load before any allocation, launch or multi-step run on a Slurm system, or on `Invalid generic resource (gres) specification` / `Requested node configuration is not available` for multi-node jobs, `Nodes_required_for_job_are_DOWN,_DRAINED_or_reserved_for_jobs_in_higher_priority_partitions`, a second srun step that waits forever, a daemon step that exits 0 with empty/0-byte output, or `cudaErrorInvalidDevice` under --gpus-per-task."""
import json
import re


def _flatten(v):
    if isinstance(v, str):
        return v.splitlines()
    if isinstance(v, dict):
        return [x for i in v.values() for x in _flatten(i)]
    if isinstance(v, list):
        return [x for i in v for x in _flatten(i)]
    return []


def _SOFTWARE_SLURM_ALLOC_judge(commands, rules):
    """Apply the rules (forbid / require / require_if / forbid_if regexes) to the proposed commands."""
    items = commands
    if isinstance(commands, str):
        s = commands.strip()
        if s[:1] in "[{":
            try:
                items = json.loads(s)
            except ValueError:
                items = s
    lines = [ln for ln in _flatten(items) if ln.strip()]
    if not lines:
        return {"status": "inconclusive", "checks": [], "verdicts": {},
                "detail": "no commands given: pass the proposed command lines or recipe"}
    text = "\n".join(lines)
    out, verdicts = [], {}
    for r in rules:
        fl = re.I if "i" in r.get("flags", "") else 0
        pat = re.compile(r["pattern"], fl)
        when = re.compile(r["when"], fl) if r.get("when") else None
        kind = r["kind"]
        applies = when is None or bool(when.search(text))
        ok, detail = True, "not applicable"
        if applies and kind in ("forbid", "forbid_if"):
            bad = [ln for ln in lines if pat.search(ln)]
            ok = not bad
            detail = ("found: " + bad[0][:160]) if bad else "absent, as required"
        elif applies and kind in ("require", "require_if"):
            ok = bool(pat.search(text))
            detail = "present" if ok else "missing: " + r["pattern"]
        verdicts[r["id"]] = "n/a" if not applies else ("pass" if ok else "fail")
        out.append({"check": r["id"], "ok": ok, "detail": detail if ok else detail + " -- " + r["why"],
                    "fix": "" if ok else r["fix"]})
    return {"status": "fail" if any(not c["ok"] for c in out) else "pass", "checks": out, "verdicts": verdicts}


def register(mcp):

    @mcp.tool()
    def software_slurm_alloc_recipe(section: str = "") -> str:
        """The build/run/env recipe software_slurm_alloc knows, as structured JSON: allocate, cancel, discover, env_traps, estimate, gpus, pending_reasons, run, sweeps, verify.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (allocate, cancel, discover, env_traps, estimate, gpus, pending_reasons, run, sweeps, verify); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_slurm_alloc_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_SLURM_ALLOC_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_slurm_alloc", "sections": sorted(_SOFTWARE_SLURM_ALLOC_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_SLURM_ALLOC_RULES]})

    @mcp.tool()
    def software_slurm_alloc_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_slurm_alloc's rules: no_scancel_all_user_jobs; overlap_for_steps_in_allocation; no_pkill_f; check_maxnodes_before_multinode; kill_on_bad_exit_for_gpu_app; no_backslash_then_comment; no_module_in_bash_lc.

        Use on a proposed recipe or command list before running it, and after software_slurm_alloc_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_SLURM_ALLOC_judge(commands, _SOFTWARE_SLURM_ALLOC_RULES))


_SOFTWARE_SLURM_ALLOC_RECIPE = {'discover': {'partitions': 'sinfo -o "%20P %5a %10l %6D %10T %N"',
              'limits': "scontrol show partition <name> | tr ' ' '\\n' | grep -E "
                        '"MaxNodes|MaxTime|TotalNodes|State"',
              'node': 'scontrol show node <node> | head -20  # Gres, CPUTot, Sockets, RealMemory',
              'shared_nodes': 'sinfo -h -p <part> -o %N  # compare lists'},
 'estimate': {'command': 'sbatch -p <part> -N<n> -t <min> --gres=gpu:4 --test-only --wrap="hostname"',
              'poll': 'squeue -j <jobid> -o "%.10i %.8T %.20S %R"',
              'backlog': 'squeue -p <part> -h -t PENDING | wc -l'},
 'allocate': {'interactive': 'salloc -p <part> -N<n> -t <min> --gres=gpu:4 --no-shell',
              'batch_nonblocking': 'sbatch --parsable -p <part> -N<n> -t <min> --gres=gpu:4 --job-name=<name> -o '
                                   '<logdir>/%x_%j.log --wrap "<script> <args>"',
              'batch_blocking': 'sbatch --wait ... (background driver only)',
              'time_left': 'squeue -h -j <jobid> -o "%L"',
              'end_time': 'squeue -h -j <jobid> -o "%e"',
              'policy': 'ask the user first; prefer a standing allocation'},
 'run': {'step': 'srun --jobid=<ALLOC_JOBID> --overlap -N<n> -n<tasks> <cmd>',
         'env': {'SLURM_JOB_ID': 'allocation id',
                 'SLURM_JOB_NODELIST': 'compressed nodelist (scontrol show hostnames)',
                 'SLURM_LOCALID': 'rank within node',
                 'SLURM_PROCID': 'global rank'},
         'hosts': 'mapfile -t HOSTS < <(scontrol show hostnames "$SLURM_JOB_NODELIST")',
         'slice': 'SLICE=$(IFS=,; echo "${HOSTS[*]:$((s*N)):$N}")',
         'daemon_step': 'srun -N$N -n$N -c1 --nodelist="$SLICE" --overlap bash -c \'<start>; while [ ! -f '
                        '"$STOP_FLAG" ]; do sleep 1; done; <stop>; for _i in $(seq 1 60); do [ -s "$OUT" ] && break; '
                        "sleep 1; done' &",
         'app_step': 'timeout "$APP_TIMEOUT" srun -N$N -n$((N*P)) --nodelist="$SLICE" --overlap --gres=gpu:4 '
                     '--kill-on-bad-exit=1 <app>'},
 'gpus': {'--gres=gpu:4': 'all 4 visible per task',
          '--gpus-per-task=1': '1 visible, renumbered to 0',
          'verify': "srun --jobid=$J --overlap -N1 -n2 --gres=gpu:4 bash -c 'echo localid=$SLURM_LOCALID "
                    "CVD=$CUDA_VISIBLE_DEVICES'"},
 'env_traps': ['no trailing backslash + comment line; use ( export ...; srun ... )',
               'module loads in a sourced script, verify with which (not bash -lc)',
               'sourced env scripts end with true'],
 'cancel': {'one_job': 'scancel <JOBID>',
            'find': 'squeue -h -u "$USER" -o "%i %j"',
            'scoped': 'scancel --state=PENDING --name=<jobname> -u $USER',
            'never': ['scancel -u $USER', 'cancel the allocation', 'pkill -f <pattern matching own shell>']},
 'sweeps': {'state_file': 'append one line per verified unit; skip on restart',
            'checkpoint_on': 'artifacts counted and non-empty, never rc',
            'deadline_guard': 'END=$(squeue -h -j "$SLURM_JOB_ID" -o %e); DEADLINE=$(date -d "$END" +%s); [ '
                              '$((DEADLINE-$(date +%s))) -gt $((MAXOBS*2+120)) ] || exit 7',
            'scales': 'one non-blocking sbatch per scale, concurrently'},
 'pending_reasons': {'Priority': 'higher-priority jobs ahead; normal',
                     'Resources': 'waiting for free nodes',
                     'Nodes required ... higher priority partitions': 'shared nodes held by another partition; not a '
                                                                      'fault',
                     'QOSMaxJobsPerUserLimit/AssocMaxJobsLimit': 'too many jobs queued',
                     'ReqNodeNotAvail': 'DOWN/DRAINED node in explicit --nodelist'},
 'verify': {'sacct': 'sacct -j <jobid> -o JobID,JobName,State,ExitCode,NNodes,NTasks,Elapsed,Start,End',
            'scontrol': 'scontrol show job <jobid> | grep -E "JobState|Reason|NumNodes|NumTasks"',
            'disqualify': ['TIMEOUT', 'CANCELLED', 'NODE_FAIL', 'non-zero ExitCode'],
            'replicates': '>=5, p50/p95/min/max'}}

_SOFTWARE_SLURM_ALLOC_RULES = [{'id': 'no_scancel_all_user_jobs',
  'kind': 'forbid',
  'pattern': '\\bscancel\\s+(-u|--user)[ =]?\\S+\\s*$',
  'why': 'scancel -u $USER kills every job the user has, including allocations and work that is not yours.',
  'fix': 'scancel <JOBID> you submitted, or scope with --state=PENDING --name=<jobname> -u $USER.'},
 {'id': 'overlap_for_steps_in_allocation',
  'kind': 'forbid',
  'pattern': '^(?!.*--overlap).*\\bsrun\\b[^\\n]*--jobid',
  'why': 'Without --overlap a step on resources held by another step waits forever.',
  'fix': 'Add --overlap to srun --jobid=<alloc> steps.'},
 {'id': 'no_pkill_f',
  'kind': 'forbid',
  'pattern': '\\bpkill\\s+(-\\w*\\s+)*-f\\b',
  'why': "pkill -f can match the invoking shell's own command line and kill the cleanup itself.",
  'fix': 'Find pids and check /proc/<pid>/cmdline, or use a pattern that cannot match the invoking command.'},
 {'id': 'check_maxnodes_before_multinode',
  'kind': 'require_if',
  'pattern': 'scontrol\\s+show\\s+partition|sbatch\\s[^\\n]*--test-only',
  'when': '\\b(salloc|sbatch|srun)\\b[^\\n]*\\s-N\\s*([2-9]|\\d{2,})',
  'why': 'Per-partition MaxNodes can cap a job at one node; the rejection messages blame GRES/node configuration '
         'instead.',
  'fix': 'Run scontrol show partition <p> (MaxNodes) and/or sbatch --test-only for the shape first.'},
 {'id': 'kill_on_bad_exit_for_gpu_app',
  'kind': 'require_if',
  'pattern': '--kill-on-bad-exit',
  'when': '\\bsrun\\b[^\\n]*--gres=gpu',
  'why': 'One aborted rank leaves its peers blocked in the next collective forever.',
  'fix': 'timeout $APP_TIMEOUT srun ... --kill-on-bad-exit=1 ...'},
 {'id': 'no_backslash_then_comment',
  'kind': 'require',
  'pattern': '\\A(?![\\s\\S]*\\\\\\n[ \\t]*#)',
  'why': 'A trailing backslash followed by a comment line ends the command; prefix env assignments are silently '
         'dropped.',
  'fix': 'Use ( export FOO=1 BAR=2; srun ... ) or remove the comment line from the continuation.'},
 {'id': 'no_module_in_bash_lc',
  'kind': 'forbid',
  'pattern': 'bash\\s+-l\\w*c?\\b[^\\n]*\\bmodule\\s+(purge|load)',
  'why': 'The login profile of bash -lc reloads site defaults and can roll back module purge/load.',
  'fix': 'Put module loads in a sourced script and verify with which.'}]
