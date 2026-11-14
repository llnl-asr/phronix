"""software_papi: PAPI hardware-counter tracing with dftracer (DFTRACER_ENABLE_PAPI_TRACING, DFTRACER_PAPI_EVENTS, DFTRACER_PAPI_SAMPLE_INTERVAL_MS, DFTRACER_PAPI_MULTIPLEX): the real hardware-counter budget from papi_avail (not the preset count), derived presets that cost several counters and silently multiplex or get dropped, building an exact counter partition one run per set, verifying exactness from args.multiplex and the counters that landed in the trace, probing on a compute node, the family-grouped event layout (cat == 'papi'), teardown races, and the papi/7.2.0.2 site pin. Load for any DFTRACER_ENABLE_PAPI_TRACING work, or on: 'counters were requested but this machine has M hardware counters, so they are time-shared', 'PAPI counter PAPI_X is one native event subtracted from another ... dropping it', requested counters missing from the trace, args.multiplex == 1, analyses filtering cat CACHE/FLOP/BRANCH/TLB reading zero, SIGSEGV in PAPI_library_init, crash in gotcha_get_wrappee at finalize, zero-byte traces on long runs."""
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


def _SOFTWARE_PAPI_judge(commands, rules):
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
    def software_papi_recipe(section: str = "") -> str:
        """The build/run/env recipe software_papi knows, as structured JSON: budget, drop_warning, env, layout, mi300a_examples, multiplex_warning, partition_method, sapphire_rapids_groups, site_pins, teardown, verify.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (budget, drop_warning, env, layout, mi300a_examples, multiplex_warning, partition_method, sapphire_rapids_groups, site_pins, teardown, verify); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_papi_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_PAPI_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_papi", "sections": sorted(_SOFTWARE_PAPI_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_PAPI_RULES]})

    @mcp.tool()
    def software_papi_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_papi's rules: no_papi_7_3_on_tuolumne; papi_events_plain_preset_names; papi_events_named_explicitly; no_papi_multiplex; papi_budget_checked; papi_on_compute_node; no_old_papi_categories.

        Use on a proposed recipe or command list before running it, and after software_papi_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_PAPI_judge(commands, _SOFTWARE_PAPI_RULES))


_SOFTWARE_PAPI_RECIPE = {'budget': {'command': 'papi_avail -a | head -25',
            'read': 'Number Hardware Counters : N',
            'derived_column': 'Deriv Yes = >= 2 native events',
            'examples': {'mi300a': {'hardware_counters': 5, 'presets': 30},
                         'sapphire_rapids_matrix_class': {'hardware_counters': 19,
                                                          'presets': 17,
                                                          'fit_at_once': 10,
                                                          'papi': '5.6.0.0'}}},
 'env': {'DFTRACER_ENABLE_PAPI_TRACING': '1',
         'DFTRACER_PAPI_EVENTS': 'comma/semicolon list of PAPI_* preset names, no family prefix (overrides '
                                 'build-time DFTRACER_PAPI_DETECTED_EVENTS)',
         'DFTRACER_PAPI_SAMPLE_INTERVAL_MS': '100',
         'DFTRACER_PAPI_MULTIPLEX': 'only when time-sharing is deliberately wanted'},
 'multiplex_warning': 'PAPI: N counters were requested but this machine has M hardware counters, so they are '
                      'time-shared and every multiplexed reading is a scaled estimate (measured error 1% to 6%, '
                      'worse on a workload with phases).',
 'drop_warning': 'PAPI counter <X> is one native event subtracted from another and the PAPI family does not fit this '
                 'machine; dropping it',
 'partition_method': ['one run per set',
                      'keep families together',
                      'PAPI_TOT_CYC in every set when normalizing',
                      'probe each set on a compute node at toy size',
                      'commit only sets with multiplex=0 and nothing missing'],
 'verify': {'fields': {'args.multiplex': '0 exact / 1 scaled estimate',
                       'landed': "[k for k in args if k.startswith('PAPI_') and not k.endswith('_delta')]"},
            'exact_iff': 'multiplex == 0 everywhere AND landed == requested',
            'per_sample': 'PAPI_X cumulative + PAPI_X_delta'},
 'layout': {'cat': 'papi',
            'family_in': 'event name',
            'old_cats_removed': ['CACHE', 'FLOP', 'BRANCH', 'TLB', 'INSTRUCTION', 'CYCLE'],
            'minife_30_counters': {'events_per_rank': '56,840 -> 11,223 (-80.3%)',
                                   'raw_bytes': '929,972 -> 775,296 (-16.6%)',
                                   'compacted_bytes': '1,464,837 -> 1,147,354 (-21.7%)'}},
 'teardown': {'order': 'stop PAPI sampler before posix_instance->unbind() in DFTracerCore::finalize()',
              'crash_site': 'gotcha_get_wrappee() via PAPI_read -> read(2)',
              'check': ['count zero-byte traces', 'check trailing end event']},
 'site_pins': {'tuolumne': {'good': 'papi/7.2.0.2',
                            'bad': 'papi/7.3.0.1 (rocp_sdk ABI mismatch -> SIGSEGV in PAPI_library_init)'}},
 'sapphire_rapids_groups': {'BRANCH': ['PAPI_BR_UCN',
                                       'PAPI_BR_CN',
                                       'PAPI_BR_TKN',
                                       'PAPI_BR_NTK',
                                       'PAPI_BR_MSP',
                                       'PAPI_BR_PRC',
                                       'PAPI_BR_INS'],
                            'INSTRUCTION': ['PAPI_TOT_INS'],
                            'CYCLE': ['PAPI_TOT_CYC', 'PAPI_REF_CYC'],
                            'FLOP': ['PAPI_FP_INS',
                                     'PAPI_VEC_INS',
                                     'PAPI_FP_OPS',
                                     'PAPI_SP_OPS',
                                     'PAPI_DP_OPS',
                                     'PAPI_VEC_SP',
                                     'PAPI_VEC_DP'],
                            'exact_partition': {'set1_branch_cycle': 'PAPI_BR_UCN,PAPI_BR_CN,PAPI_BR_TKN,PAPI_BR_NTK,PAPI_BR_MSP,PAPI_BR_PRC,PAPI_BR_INS,PAPI_TOT_INS,PAPI_TOT_CYC,PAPI_REF_CYC',
                                                'set2_flop': 'PAPI_FP_INS,PAPI_VEC_INS,PAPI_FP_OPS,PAPI_SP_OPS,PAPI_DP_OPS,PAPI_VEC_SP,PAPI_VEC_DP'},
                            'all_17_result': "mux=[1] want=17 got=15 missing=['PAPI_BR_UCN','PAPI_BR_PRC']",
                            'mixed_4_result': 'TOT_INS,TOT_CYC,FP_OPS,DP_OPS -> MULTIPLEXED'},
 'mi300a_examples': {'multiplexed_5': 'PAPI_BR_MSP,PAPI_BR_PRC(D),PAPI_FP_OPS,PAPI_FP_INS(D),PAPI_FMA_INS(D) -> '
                                      'multiplex=1, BR_PRC dropped',
                     'fits': 'PAPI_L2_ICM(D), PAPI_L2_TCM(D) + three native',
                     'exact_on_compute': 'PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS'}}

_SOFTWARE_PAPI_RULES = [{'id': 'no_papi_7_3_on_tuolumne',
  'kind': 'forbid',
  'pattern': 'module\\s+load\\s+[^\\n]*\\bpapi/7\\.3',
  'why': 'papi/7.3.0.1 ships a rocp_sdk component ABI-incompatible with the installed ROCm: SIGSEGV in '
         'PAPI_library_init (build probe falls back to two counters, app dies).',
  'fix': 'module load papi/7.2.0.2.'},
 {'id': 'papi_events_plain_preset_names',
  'kind': 'forbid',
  'pattern': 'DFTRACER_PAPI_EVENTS=[\'\\"]?(?:PAPI_\\w+[,;])*(?!PAPI_|\\$)[^\\s,;\'\\"]',
  'why': 'DFTRACER_PAPI_EVENTS takes plain PAPI_* preset names separated by , or ; (no family prefix).',
  'fix': 'Use e.g. DFTRACER_PAPI_EVENTS=PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_L1_DCM.'},
 {'id': 'papi_events_named_explicitly',
  'kind': 'require_if',
  'pattern': 'DFTRACER_PAPI_EVENTS=\\S',
  'when': 'DFTRACER_ENABLE_PAPI_TRACING=(1|ON)',
  'why': 'Exact counts need one explicitly named set per run; the build-time default may exceed the hardware budget.',
  'fix': 'Set DFTRACER_PAPI_EVENTS to a probed set that fits (multiplex=0).'},
 {'id': 'no_papi_multiplex',
  'kind': 'forbid',
  'pattern': 'DFTRACER_PAPI_MULTIPLEX=(1|on|true|yes)',
  'flags': 'i',
  'why': 'Multiplexed readings are biased scaled estimates (1-6%, worse with phases), not measurements.',
  'fix': 'Unset DFTRACER_PAPI_MULTIPLEX and split the counters into one run per fitting set.'},
 {'id': 'papi_budget_checked',
  'kind': 'require_if',
  'pattern': 'papi_avail',
  'when': 'DFTRACER_ENABLE_PAPI_TRACING=(1|ON)',
  'why': 'The budget is the hardware counter count from papi_avail, not the preset count.',
  'fix': "Run `papi_avail -a | head -25` on the compute node and read 'Number Hardware Counters'."},
 {'id': 'papi_on_compute_node',
  'kind': 'require_if',
  'pattern': '\\bflux\\s+(run|proxy|submit|batch|alloc)\\b|\\bsrun\\b|\\bsalloc\\b|\\bsbatch\\b',
  'when': 'DFTRACER_ENABLE_PAPI_TRACING=(1|ON)',
  'why': 'multiplex is a property of the node: a login-node run gives the wrong verdict.',
  'fix': 'Run the probe and the real run on compute nodes (flux run / srun inside an allocation).'},
 {'id': 'no_old_papi_categories',
  'kind': 'forbid',
  'pattern': 'cat\\s*==\\s*[\'\\"]?(CACHE|FLOP|BRANCH|TLB|INSTRUCTION|CYCLE)\\b',
  'why': "PAPI events are family-grouped under cat == 'papi'; the old per-family categories no longer exist and read "
         'zero.',
  'fix': 'Filter cat == "papi" and use the event name as the family.'}]
