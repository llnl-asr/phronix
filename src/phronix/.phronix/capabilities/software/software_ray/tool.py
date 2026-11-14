"""software_ray: Ray (Ray Core / Train / Tune / Data) cluster bring-up on Cray PE + ROCm systems: the jemalloc LD_PRELOAD / static-TLS crash that makes `ray start --head` fail (export LD_PRELOAD="" before every ray start), multi-node manual bootstrap pitfalls (RAY_ADDRESS for ray.init, head --num-gpus, worker lifetime), and trace-reading caveats (ray.data materializes once; plasma_store paths in default_worker.py cmdlines). Load for any Ray workload, or on `Failed to connect to GCS at address ... within 5 seconds`, `Failed to get cluster ID from GCS server: TimedOut`, `FileNotFoundError: ... logs/gcs_server.err`, `cannot allocate memory in static TLS block`, a Ray Train job hanging at ~0% CPU waiting for resources, or epoch-boundary POSIX metadata bursts in a ray.data pipeline."""
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


def _SOFTWARE_RAY_judge(commands, rules):
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
    def software_ray_recipe(section: str = "") -> str:
        """The build/run/env recipe software_ray knows, as structured JSON: diagnose, env, failure_signature, head, trace_reading, verified_versions, worker.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (diagnose, env, failure_signature, head, trace_reading, verified_versions, worker); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_ray_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_RAY_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_ray", "sections": sorted(_SOFTWARE_RAY_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_RAY_RULES]})

    @mcp.tool()
    def software_ray_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_ray's rules: empty_ld_preload_before_ray_start; ray_address_for_init; head_keeps_gpus; no_fixed_sleep_before_ray_stop; filter_worker_cmdlines_for_spill.

        Use on a proposed recipe or command list before running it, and after software_ray_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_RAY_judge(commands, _SOFTWARE_RAY_RULES))


_SOFTWARE_RAY_RECIPE = {'env': {'LD_PRELOAD': '"" (empty string, set before every ray start; unset is NOT enough)',
         'RAY_ADDRESS': '<head_ip>:<port> in every driver calling ray.init()'},
 'head': {'command': 'ray start --head --port=<port> [--num-gpus=<all on node>]',
          'avoid': '--num-gpus=0/--num-cpus=0 on an accelerator compute node',
          'expected': 'up in ~10 s; ray status lists the node'},
 'worker': {'command': 'ray start --address=<head_ip>:<port>',
            'lifetime': 'poll completion-marker file from the head, then ray stop',
            'avoid': 'sleep N; ray stop'},
 'failure_signature': ['gcs_rpc_client.h:151: Failed to connect to GCS at address <ip>:<port> within 5 seconds',
                       'gcs_client.cc:183: Failed to get cluster ID from GCS server: TimedOut',
                       'FileNotFoundError: ... session_.../logs/gcs_server.err',
                       'cannot allocate memory in static TLS block',
                       'timing: ~35 s (5 s GCS connect + 30 s cluster-ID retry)'],
 'diagnose': ['read ray/_private/services.py start_gcs_server/start_raylet command list',
              'run that binary by hand with/without the env var',
              'diff against start_ray_process env (os.environ.copy() + env_updates)',
              'check LD_PRELOAD injection first (propagate_jemalloc_env_var)'],
 'trace_reading': {'ray_data_read_csv': 'materialized once into the object store; workers do not re-read the file',
                   'import_storm': '__lxstat64 bursts on site-packages from newly spawned workers',
                   'spill_filter': 'events from TraceViewer (tools_dftracer_utils) | grep -v default_worker.py | '
                                   "grep '<ray_temp_dir>'"},
 'verified_versions': {'ray': '2.48.0', 'rocm': '6.2.1', 'python': '3.9', 'system': 'Tuolumne Cray PE'}}

_SOFTWARE_RAY_RULES = [{'id': 'empty_ld_preload_before_ray_start',
  'kind': 'require_if',
  'pattern': 'LD_PRELOAD=(\\"\\"|\'\'|(?=\\s|$))',
  'when': '\\bray\\s+start\\b',
  'why': 'Ray injects libjemalloc.so via LD_PRELOAD when it is unset; on Cray PE + ROCm this dies in static TLS and '
         'ray start times out.',
  'fix': 'export LD_PRELOAD="" before every ray start (head and workers).'},
 {'id': 'ray_address_for_init',
  'kind': 'require_if',
  'pattern': 'RAY_ADDRESS=',
  'when': 'ray\\.init\\(\\s*\\)',
  'why': 'ray.init() without RAY_ADDRESS starts an isolated cluster; multi-node resource requests then hang forever.',
  'fix': 'export RAY_ADDRESS=<head_ip>:<port> before the driver.'},
 {'id': 'head_keeps_gpus',
  'kind': 'forbid',
  'pattern': 'ray\\s+start\\s+[^\\n]*--head[^\\n]*--num-gpus[ =]0\\b|ray\\s+start\\s+[^\\n]*--num-gpus[ '
             '=]0\\b[^\\n]*--head',
  'why': 'A compute-node head with --num-gpus=0 under-resources the cluster relative to ScalingConfig math.',
  'fix': 'Let the head contribute its devices (omit --num-gpus or set the real count).'},
 {'id': 'no_fixed_sleep_before_ray_stop',
  'kind': 'forbid',
  'pattern': '\\bsleep\\s+\\d+\\s*(;|&&)\\s*ray\\s+stop\\b',
  'why': 'A fixed sleep before ray stop races the head-side job duration.',
  'fix': 'Poll a completion-marker file written by the head, with a generous upper bound, then ray stop.'},
 {'id': 'filter_worker_cmdlines_for_spill',
  'kind': 'forbid',
  'pattern': '^(?!.*default_worker\\.py).*\\bgrep\\b[^|\\n]*plasma_store',
  'why': 'default_worker.py cmdlines embed --object-store-name=.../plasma_store and false-positive as spill I/O.',
  'fix': 'Insert grep -v default_worker.py before the plasma_store / <ray_temp_dir> match (on events read through '
         'TraceViewer).'}]
