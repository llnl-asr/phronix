"""system_tuolumne_rabbit: Rabbit near-node-flash (NVMe) storage on Tuolumne as an L3 filesystem optimization: picking SHM vs XFS vs GFS2 vs Lustre-on-Rabbit by data-sharing scope and size, the DataWarp directives passed to `flux alloc -S "#DW jobdw ..."` (plus `--coral2-chassis=1` for GFS2), the `$DW_JOB_<name>` mount, staging data in and results out, and the rule that the user (not the agent) creates the allocation. Load when a dftracer trace shows an I/O bottleneck a faster near-node tier would relieve, when `$DW_JOB_*` is empty/unset inside a job (the allocation lacked #DW flags), or when choosing where a job's scratch data should live on Tuolumne."""
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


def _SYSTEM_TUOLUMNE_RABBIT_judge(commands, rules):
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
    def system_tuolumne_rabbit_recipe(section: str = "") -> str:
        """The build/run/env recipe system_tuolumne_rabbit knows, as structured JSON: launch, optimization_level, permissions, reference, thresholds, tiers, verify, when_not, workflow, wrapper_example.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (launch, optimization_level, permissions, reference, thresholds, tiers, verify, when_not, workflow, wrapper_example); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what system_tuolumne_rabbit_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SYSTEM_TUOLUMNE_RABBIT_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "system_tuolumne_rabbit", "sections": sorted(_SYSTEM_TUOLUMNE_RABBIT_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SYSTEM_TUOLUMNE_RABBIT_RULES]})

    @mcp.tool()
    def system_tuolumne_rabbit_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against system_tuolumne_rabbit's rules: dw_on_alloc_not_run; gfs2_needs_chassis; gfs2_striped_access; gfs2_max_16_nodes; dw_needs_capacity_and_name; traces_not_on_rabbit; no_sudo; agent_runs_via_proxy_wrapper.

        Use on a proposed recipe or command list before running it, and after system_tuolumne_rabbit_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SYSTEM_TUOLUMNE_RABBIT_judge(commands, _SYSTEM_TUOLUMNE_RABBIT_RULES))


_SYSTEM_TUOLUMNE_RABBIT_RECIPE = {'tiers': [{'tier': 'shm',
            'scope': 'processes on one node',
            'size': '<= ~20% of node memory',
            'how': '/dev/shm (tmpfs)',
            'dw': None},
           {'tier': 'xfs',
            'scope': 'processes on one node',
            'size': '> 20% of node memory, up to 1 TB per compute node',
            'how': '#DW jobdw type=xfs',
            'dw': '#DW jobdw type=xfs capacity=1TiB name=scratch',
            'env': '$DW_JOB_scratch'},
           {'tier': 'gfs2',
            'scope': 'processes across <= 16 nodes of one chassis',
            'size': "fits one Rabbit's flash",
            'how': '--coral2-chassis=1 + #DW jobdw type=gfs2 access_mode=striped',
            'dw': '#DW jobdw type=gfs2 capacity=4TiB name=shared access_mode=striped',
            'env': '$DW_JOB_shared'},
           {'tier': 'lustre',
            'scope': 'processes across > 16 nodes / whole job',
            'size': 'large / cluster-wide',
            'how': '#DW jobdw type=lustre access_mode=striped',
            'dw': '#DW jobdw type=lustre capacity=16TiB name=big access_mode=striped',
            'env': '$DW_JOB_big'}],
 'thresholds': {'shm_max_fraction_of_node_memory': 0.2,
                'xfs_max_per_compute_node': '1TB',
                'gfs2_max_nodes': 16,
                'lustre_on_rabbit_min_nodes': 17},
 'launch': {'xfs': 'flux alloc -N 1 -q <QUEUE> -t <TIME> -S "#DW jobdw type=xfs capacity=1TiB name=scratch"',
            'gfs2': 'flux alloc -N 16 --coral2-chassis=1 -q <QUEUE> -t <TIME> -S "#DW jobdw type=gfs2 capacity=4TiB '
                    'name=shared access_mode=striped"',
            'lustre': 'flux alloc -N 64 -q <QUEUE> -t <TIME> -S "#DW jobdw type=lustre capacity=16TiB name=big '
                      'access_mode=striped"',
            'directive_flag': '-S "#DW jobdw type=<xfs|gfs2|lustre> capacity=<N>TiB name=<name> '
                              '[access_mode=striped]"',
            'mount_env': '$DW_JOB_<name> (name= from the directive)',
            'where': 'flags on flux alloc (allocation time), never flux run'},
 'workflow': ['1. From the trace, identify data-sharing scope and reuse pattern (single-node exchange, chassis-wide '
              'shared file, cluster-wide dataset).',
              '2. Pick the tier from `tiers` (SHM -> XFS -> GFS2 -> Lustre).',
              '3. Give the user the exact flux alloc command from `launch`; the user allocates and reports the '
              'JOBID.',
              '4. flux proxy <JOBID> bash ${WORKSPACE}/workspaces/${SESSION}/tmp/<script>.sh  (wrapper sets '
              'DATA_DIR=$DW_JOB_<name>).',
              '5. In the wrapper: stage inputs onto $DW_JOB_<name> once (cp/rsync), run the app, copy persistent '
              'outputs back to /p/lustre5/$USER/... before the job ends.',
              '6. Traces stay under workspaces/${SESSION}/traces/, not on the Rabbit mount.'],
 'wrapper_example': ['#!/bin/bash',
                     'export DATA_DIR="$DW_JOB_scratch"',
                     'rsync -a /p/lustre5/$USER/<dataset>/ "$DATA_DIR"/',
                     'export DFTRACER_LOG_FILE=${WORKSPACE}/workspaces/${SESSION}/traces/<run>/trace',
                     'flux run -N 1 -n <ranks> <app> --data "$DATA_DIR"',
                     'rsync -a "$DATA_DIR"/<outputs>/ /p/lustre5/$USER/<outputs>/'],
 'verify': ['df "$DW_JOB_<name>"', 'stat "$DW_JOB_<name>"'],
 'when_not': ['metadata- or small-I/O-bound at the app layer: fix L1/L2 first', 'dataset already fits in SHM'],
 'optimization_level': 'L3 (filesystem/system): no source change',
 'permissions': {'bash': ['flux', 'cp', 'rsync', 'df', 'stat'],
                 'write': 'workspaces/<session>/* (wrappers under tmp/)',
                 'sudo': 'never'},
 'reference': 'https://nearnodeflash.github.io/v0.1.27/guides/storage-profiles/readme/#setting-the-default-profile'}

_SYSTEM_TUOLUMNE_RABBIT_RULES = [{'id': 'dw_on_alloc_not_run',
  'kind': 'forbid',
  'pattern': 'flux\\s+run\\b.*#DW',
  'why': 'DW directives provision storage at allocation time; flux run cannot add them.',
  'fix': 'Move the -S "#DW jobdw ..." directive onto the flux alloc command the user runs.'},
 {'id': 'gfs2_needs_chassis',
  'kind': 'require_if',
  'pattern': '--coral2-chassis=1',
  'when': 'type=gfs2',
  'why': 'GFS2 shared access needs one Rabbit backing all (<=16) nodes of a chassis.',
  'fix': 'Add --coral2-chassis=1 to the flux alloc line.'},
 {'id': 'gfs2_striped_access',
  'kind': 'require_if',
  'pattern': 'type=gfs2[^\\"\\n]*access_mode=striped',
  'when': 'type=gfs2',
  'why': 'Nodes share one GFS2 filesystem only with shared/striped access.',
  'fix': 'Add access_mode=striped to the gfs2 #DW directive.'},
 {'id': 'gfs2_max_16_nodes',
  'kind': 'forbid',
  'pattern': '-N\\s*(1[7-9]|[2-9]\\d|\\d{3,})\\b.*type=gfs2',
  'why': 'GFS2 on one Rabbit spans at most 16 compute nodes of a chassis; beyond that use Lustre on Rabbits.',
  'fix': 'Use #DW jobdw type=lustre ... access_mode=striped for > 16 nodes.'},
 {'id': 'dw_needs_capacity_and_name',
  'kind': 'require_if',
  'pattern': '#DW\\s+jobdw\\s+(?=[^\\"\\n]*capacity=\\S+)(?=[^\\"\\n]*name=\\S+)',
  'when': '#DW\\s+jobdw',
  'why': 'The directive sizes the allocation (capacity=) and names the $DW_JOB_<name> mount (name=).',
  'fix': 'Give the #DW jobdw directive both capacity=<N>TiB and name=<name>.'},
 {'id': 'traces_not_on_rabbit',
  'kind': 'forbid',
  'pattern': '(DFTRACER_LOG_FILE|DFTRACER_DATA_DIR|traces?_dir)\\s*=\\s*[\\"\']?\\$\\{?DW_JOB',
  'why': 'Rabbit mounts are torn down with the job; dftracer traces belong in workspaces/<session>/traces/.',
  'fix': 'Point DFTRACER_LOG_FILE at ${WORKSPACE}/workspaces/${SESSION}/traces/<run>/.'},
 {'id': 'no_sudo',
  'kind': 'forbid',
  'pattern': '(^|[;&|]\\s*)sudo\\b',
  'why': 'Rabbit provisioning is unprivileged, via DW directives only.',
  'fix': 'Drop sudo; request storage with -S "#DW jobdw ..." on flux alloc.'},
 {'id': 'agent_runs_via_proxy_wrapper',
  'kind': 'require_if',
  'pattern': 'flux\\s+proxy\\s+\\S+\\s+bash\\s+\\S+\\.sh',
  'when': '\\$\\{?DW_JOB_',
  'why': "The agent runs inside the user's allocation through a wrapper script; the DW path goes in the wrapper.",
  'fix': 'Run flux proxy <JOBID> bash <ws>/tmp/<script>.sh and set DATA_DIR=$DW_JOB_<name> inside it.'}]
